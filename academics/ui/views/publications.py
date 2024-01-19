from flask import (abort, flash, jsonify, redirect, render_template, request,
                   url_for)
from flask_login import current_user
from flask_security import roles_accepted
from lbrc_flask.database import db
from lbrc_flask.export import excel_download, pdf_download
from lbrc_flask.forms import FlashingForm, MultiCheckboxField
from lbrc_flask.json import validate_json
from lbrc_flask.security import current_user_id
from lbrc_flask.validators import parse_date_or_none
from wtforms import HiddenField
from academics.model.academic import Academic, CatalogPublicationsSources, Source
from academics.model.folder import Folder
from academics.model.publication import (CatalogPublication, Journal, Keyword,
                             NihrAcknowledgement, Publication, Sponsor,
                             Subtype)
from academics.catalogs.service import auto_validate
from academics.model.security import User
from academics.model.theme import Theme
from academics.services.publication_searching import PublicationSearchForm, ValidationSearchForm, academic_select_choices, folder_select_choices, journal_select_choices, keyword_select_choices, catalog_publication_search_query, publication_search_query
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from .. import blueprint


class PublicationFolderForm(FlashingForm):
    publication_id = HiddenField('publication_id')
    folder_ids = MultiCheckboxField('Folders', coerce=int)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.folder_ids.choices = folder_select_choices()


@blueprint.route("/publications/")
def publications():
    search_form = PublicationSearchForm(formdata=request.args)
    
    q = publication_search_query(search_form)
    q = q.options(
        selectinload(Publication.catalog_publications)
        .selectinload(CatalogPublication.catalog_publication_sources)
        .selectinload(CatalogPublicationsSources.source)
        .selectinload(Source.academic)
    )
    q = q.options(
        selectinload(Publication.folders)
    )
    q = q.order_by(CatalogPublication.publication_cover_date.desc())

    publications = db.paginate(
        select=q,
        page=search_form.page.data,
        per_page=5,
        error_out=False,
    )

    search_form.keywords.choices = [(k.id, k.keyword.title()) for k in Keyword.query.filter(Keyword.id.in_(search_form.keywords.data)).all()]
    search_form.journal_id.choices = [(j.id, j.name.title()) for j in Journal.query.filter(Journal.id.in_(search_form.journal_id.data)).all()]
    search_form.academic_id.choices = [(a.id, a.full_name) for a in Academic.query.filter(Academic.id.in_(search_form.academic_id.data)).all()]

    folder_query = Folder.query

    folder_query = folder_query.filter(or_(
        Folder.owner_id == current_user_id(),
        Folder.shared_users.any(User.id == current_user_id()),
    ))

    return render_template(
        "ui/publications.html",
        search_form=search_form,
        publication_folder_form=PublicationFolderForm(),
        publications=publications,
        folders=folder_query.all(),
        nihr_acknowledgements=NihrAcknowledgement.query.all(),
    )


@blueprint.route("/validation/")
@roles_accepted('validator')
def validation():
    search_form = ValidationSearchForm(theme_id=current_user.theme_id, formdata=request.args)
    search_form.subtype_id.data = [s.id for s in Subtype.get_validation_types()]
    
    q = publication_search_query(search_form)
    q = q.order_by(CatalogPublication.publication_cover_date.asc())

    publications = db.paginate(
        select=q,
        page=search_form.page.data,
        per_page=5,
        error_out=False,
    )

    return render_template(
        "ui/validation.html",
        publications=publications,
        search_form=search_form,
        nihr_acknowledgements=NihrAcknowledgement.query.all(),
    )


@blueprint.route("/publications/folders", methods=['POST'])
@validate_json({
    'type': 'object',
    'properties': {
        'id': {'type': 'integer'},
    },
    "required": ["id"]
})
def publication_folders():
    publication = db.get_or_404(Publication, request.json.get('id'))

    folder_query = Folder.query.filter(or_(
        Folder.owner_id == current_user_id(),
        Folder.shared_users.any(User.id == current_user_id()),
    ))

    return render_template(
        "ui/publication_folders.html",
        publication=publication,
        folders=folder_query.all(),
    )


@blueprint.route("/publications/export/xslt")
def publication_full_export_xlsx():
    # Use of dictionary instead of set to maintain order of headers
    headers = {
        'catalog': None,
        'catalog_identifier': None,
        'doi': None,
        'journal': None,
        'type': None,
        'volume': None,
        'issue': None,
        'pages': None,
        'publication_cover_date': None,
        'authors': None,
        'title': None,
        'abstract': None,
        'open access': None,
        'citations': None,
        'sponsor': None,
    }

    search_form = PublicationSearchForm(formdata=request.args)

    cat_pubs = catalog_publication_search_query(search_form)
    q = select(CatalogPublication).select_from(cat_pubs).join(CatalogPublication, CatalogPublication.id == cat_pubs.c.id)
    q = q.join(CatalogPublication.journal, isouter=True)
    q = q.join(CatalogPublication.subtype, isouter=True)
    q = q.join(Publication.sponsors, isouter=True)
    q = q.group_by(CatalogPublication.id)

    q = q.with_only_columns(
        CatalogPublication.id,
        CatalogPublication.catalog,
        CatalogPublication.catalog_identifier,
        CatalogPublication.doi,
        CatalogPublication.title,
        CatalogPublication.publication_cover_date,
        CatalogPublication.issue,
        CatalogPublication.volume,
        CatalogPublication.pages,
        CatalogPublication.abstract,
        CatalogPublication.is_open_access,
        CatalogPublication.cited_by_count,
        func.coalesce(Journal.name, '').label('journal_name'),
        func.coalesce(Subtype.description, '').label('subtype_description'),
        func.group_concat(Sponsor.name.distinct()).label('sponsors')        
    )

    publication_details = ({
        'catalog': p['catalog'],
        'catalog_identifier': p['catalog_identifier'],
        'doi': p['doi'],
        'journal': p['journal_name'],
        'type': p['subtype_description'],
        'volume': p['volume'],
        'issue': p['issue'],
        'pages': p['pages'],
        'publication_cover_date': p['publication_cover_date'],
        'title': p['title'],
        'abstract': p['abstract'],
        'open access': p['is_open_access'],
        'citations': p['cited_by_count'],
        'sponsor': p['sponsors'],
    } for p in db.session.execute(q).unique().mappings())

    return excel_download('Academics_Publications', headers.keys(), publication_details)


@blueprint.route("/publications/export/annual_report")
def publication_full_annual_report_xlsx():
    # Use of dictionary instead of set to maintain order of headers
    headers = {
        'Publication Reference': None,
        'DOI': None,
    }

    search_form = PublicationSearchForm(formdata=request.args)

    cat_pubs = publication_search_query(search_form)

    q = (
        select(CatalogPublication)
        .select_from(cat_pubs)
        .join(CatalogPublication, CatalogPublication.id == cat_pubs.c.id)
        .distinct()
    )
    q = q.join(CatalogPublication.journal, isouter=True)

    q = q.with_only_columns(
        CatalogPublication.id,
        CatalogPublication.doi,
        CatalogPublication.title,
        CatalogPublication.publication_cover_date,
        CatalogPublication.issue,
        CatalogPublication.volume,
        CatalogPublication.pages,
        func.coalesce(Journal.name, '').label('journal_name'),
    )

    publication_details = ({
        'Publication Reference': Publication.vancouver(
            '',
            p['title'],
            p['journal_name'],
            p['publication_cover_date'],
            p['issue'],
            p['volume'],
            p['pages'],
        ),
        'DOI': p.doi,
    } for p in db.session.execute(q).unique().mappings())

    return excel_download('Academics_Publications', headers.keys(), publication_details)


@blueprint.route("/publications/export/pdf")
def publication_export_pdf():
    search_form = PublicationSearchForm(formdata=request.args)
    
    q = publication_search_query(search_form)

    parameters = []

    if search_form.author_id.data:
        author = db.get_or_404(Source, search_form.author_id.data)
        parameters.append(('Author', author.full_name))

    if search_form.theme_id.data:
        theme = db.get_or_404(Theme, search_form.theme_id.data)
        parameters.append(('Theme', theme.name))

    publication_start_date = parse_date_or_none(search_form.publication_start_month.data)
    if publication_start_date:
        parameters.append(('Start Publication Date', f'{publication_start_date:%b %Y}'))

    publication_end_date = parse_date_or_none(search_form.publication_end_month.data)
    if publication_end_date:
        parameters.append(('End Publication Date', f'{publication_end_date:%b %Y}'))

    # if db.session.execute(select(func.count('*')).select_from(alias(q))).scalar() > 100:
    #     abort(413)

    # q = q.options(selectinload(Publication.catalog_publications))

    publications = db.session.execute(q.order_by(CatalogPublication.publication_cover_date)).unique().scalars()

    return pdf_download(
        'ui/publications_pdf.html',
        title='Academics Publications',
        publications=publications,
        parameters=parameters,
    )


@blueprint.route("/publications/nihr_acknowledgement", methods=['POST'])
@validate_json({
    'type': 'object',
    'properties': {
        'id': {'type': 'integer'},
        'nihr_acknowledgement_id': {'type': 'integer'},
    },
    "required": ["id", "nihr_acknowledgement_id"]
})
@roles_accepted('validator')
def publication_nihr_acknowledgement():
    p = db.get_or_404(Publication, request.json.get('id'))

    if request.json.get('nihr_acknowledgement_id') == -1:
        p.nihr_acknowledgement = None
        db.session.commit()
    else:
        n = db.get_or_404(NihrAcknowledgement, request.json.get('nihr_acknowledgement_id'))

        p.nihr_acknowledgement = n

        db.session.commit()

    return jsonify({'status': 'reload'}), 205


@blueprint.route("/publication/author/options")
def publication_author_options():
    return jsonify({'results': [{'id': id, 'text': text} for id, text in academic_select_choices(request.args.get('q'))]})


@blueprint.route("/publication/keywords/options")
def publication_keyword_options():
    return jsonify({'results': [{'id': id, 'text': text} for id, text in keyword_select_choices(request.args.get('q'))]})


@blueprint.route("/publication/journal/options")
def publication_journal_options():
    return jsonify({'results': [{'id': id, 'text': text} for id, text in journal_select_choices(request.args.get('q'))]})


@blueprint.route("/publication/auto_validate")
def publication_auto_validate():
    amended_count = auto_validate()
    flash(f'{amended_count} record(s) automatically updated')
    return redirect(url_for('ui.index'))