from flask import abort, current_app, jsonify, render_template, render_template_string, request, url_for
from flask_security import roles_accepted
from lbrc_flask.database import db
from lbrc_flask.export import excel_download, pdf_download
from lbrc_flask.forms import FlashingForm, MultiCheckboxField
from lbrc_flask.security import current_user_id
from lbrc_flask.validators import parse_date_or_none
from lbrc_flask.response import trigger_response
from wtforms import HiddenField, SelectField
from academics.model.academic import Academic, CatalogPublicationsSources, Source
from academics.model.folder import Folder, FolderDoi
from academics.model.publication import CatalogPublication, Journal, Keyword, NihrAcknowledgement, Publication, Subtype
from academics.model.security import User
from academics.model.theme import Theme
from academics.services.publication_searching import PublicationSearchForm, academic_select_choices, best_catalog_publications, folder_select_choices, journal_select_choices, keyword_select_choices, publication_search_query
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from .. import blueprint


class PublicationFolderForm(FlashingForm):
    publication_id = HiddenField('publication_id')
    folder_ids = MultiCheckboxField('Folders', coerce=int)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.folder_ids.choices = folder_select_choices()


class SupplementaryAuthorAddForm(FlashingForm):
    id = HiddenField('id')
    academic_id = SelectField('Academic', coerce=int)

    def __init__(self, publication, **kwargs):
        super().__init__(**kwargs)

        academics = db.session.execute(select(Academic).where(Academic.id.notin_([a.id for a in publication.supplementary_authors])).order_by(Academic.last_name, Academic.first_name)).scalars()
        self.academic_id.choices = [(0, '')] + [(a.id, a.full_name) for a in academics]


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
        "ui/publication/index.html",
        search_form=search_form,
        publication_folder_form=PublicationFolderForm(),
        publications=publications,
        folders=folder_query.all(),
        nihr_acknowledgements=NihrAcknowledgement.query.all(),
    )


@blueprint.route("/validation/")
@blueprint.route("/validation/<int:page>")
@roles_accepted('validator')
def validation(page=1):
    q = (
        select(Publication)
        .join(Publication.catalog_publications)
        .where(CatalogPublication.id.in_(best_catalog_publications()))
        .where(CatalogPublication.subtype_id.in_([s.id for s in Subtype.get_validation_types()]))
        .where(CatalogPublication.publication_cover_date >= current_app.config['HISTORIC_PUBLICATION_CUTOFF'])
        .where(Publication.nihr_acknowledgement_id == None)
        .order_by(CatalogPublication.publication_cover_date.asc())
    )

    publications = db.paginate(
        select=q,
        page=page,
        per_page=5,
        error_out=False,
    )

    return render_template(
        "ui/publication/validation.html",
        publications=publications,
        nihr_acknowledgements=NihrAcknowledgement.query.all(),
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
        'author_count': None,
        'brc_authors': None,
        'nihr acknowledgement': None,
    }


    search_form = PublicationSearchForm(formdata=request.args)

    q = publication_search_query(search_form)
    q = q.options(
        selectinload(Publication.catalog_publications)
        .selectinload(CatalogPublication.catalog_publication_sources)
        .selectinload(CatalogPublicationsSources.source)
    )
    q = q.options(
        selectinload(Publication.catalog_publications)
        .selectinload(CatalogPublication.sponsors)
    )
    q = q.options(
        selectinload(Publication.nihr_acknowledgement)
    )

    publication_details = ({
        'catalog': p.best_catalog_publication.catalog,
        'catalog_identifier': p.best_catalog_publication.catalog_identifier,
        'doi': p.doi,
        'journal': p.best_catalog_publication.journal.name,
        'type': p.best_catalog_publication.subtype.description,
        'volume': p.best_catalog_publication.volume,
        'issue': p.best_catalog_publication.issue,
        'pages': p.best_catalog_publication.pages,
        'publication_cover_date': p.best_catalog_publication.publication_cover_date,
        'title': p.best_catalog_publication.title,
        'abstract': p.best_catalog_publication.abstract,
        'open access': p.best_catalog_publication.is_open_access,
        'citations': p.best_catalog_publication.cited_by_count,
        'sponsor': '; '.join([s.name for s in p.best_catalog_publication.sponsors]),
        'author_count': len(p.best_catalog_publication.catalog_publication_sources),
        'brc_authors': '; '.join([f'{cps.source.display_name} ({cps.ordinal + 1})' for cps in p.best_catalog_publication.catalog_publication_sources if cps.source.academic is not None]),
        'nihr acknowledgement': '' if p.nihr_acknowledgement is None else p.nihr_acknowledgement.name,
    } for p in db.session.execute(q).scalars())

    return excel_download('Academics_Publications', headers.keys(), publication_details)


@blueprint.route("/publications/export/annual_report")
def publication_full_annual_report_xlsx():
    # Use of dictionary instead of set to maintain order of headers
    headers = {
        'Publication Reference': None,
        'DOI': None,
    }

    search_form = PublicationSearchForm(formdata=request.args)

    q = publication_search_query(search_form)

    q = q.with_only_columns(
        Publication.id,
        Publication.doi,
        Publication.vancouver,
    )

    publication_details = ({
        'Publication Reference': p.vancouver,
        'DOI': p.doi,
    } for p in db.session.execute(q).unique().mappings())

    return excel_download('Academics_Publications', headers.keys(), publication_details)


@blueprint.route("/publications/export/pdf")
def publication_export_pdf():
    search_form = PublicationSearchForm(formdata=request.args)
    
    q = publication_search_query(search_form)
    q = q.options(
        selectinload(Publication.catalog_publications)
        .selectinload(CatalogPublication.catalog_publication_sources)
        .selectinload(CatalogPublicationsSources.source)
        .selectinload(Source.academic)
    )
    q = q.options(
        selectinload(Publication.folder_dois)
        .selectinload(FolderDoi.folder)
    )

    parameters = []

    if search_form.author_id.data:
        author = db.get_or_404(Source, search_form.author_id.data)
        parameters.append(('Author', author.display_name))

    if search_form.theme_id.data:
        theme = db.get_or_404(Theme, search_form.theme_id.data)
        parameters.append(('Theme', theme.name))

    publication_start_date = parse_date_or_none(search_form.publication_start_month.data)
    if publication_start_date:
        parameters.append(('Start Publication Date', f'{publication_start_date:%b %Y}'))

    publication_end_date = parse_date_or_none(search_form.publication_end_month.data)
    if publication_end_date:
        parameters.append(('End Publication Date', f'{publication_end_date:%b %Y}'))

    publications = db.session.execute(q.order_by(CatalogPublication.publication_cover_date)).unique().scalars()

    return pdf_download(
        'ui/publication/pdf.html',
        title='Academics Publications',
        publications=publications,
        parameters=parameters,
    )


@blueprint.route("/publication/author/options")
def publication_author_options():
    return jsonify({'results': [{'id': id, 'text': text} for id, text in academic_select_choices(request.args.get('q'))]})


@blueprint.route("/publication/keywords/options")
def publication_keyword_options():
    return jsonify({'results': [{'id': id, 'text': text} for id, text in keyword_select_choices(request.args.get('q'))]})


@blueprint.route("/publication/journal/options")
def publication_journal_options():
    return jsonify({'results': [{'id': id, 'text': text} for id, text in journal_select_choices(request.args.get('q'))]})


@blueprint.route("/publication/authors/<int:id>/<string:author_selector>")
def publication_authors(id, author_selector):
    q = select(Publication).where(Publication.id == id)

    q = q.options(
        selectinload(Publication.catalog_publications)
        .selectinload(CatalogPublication.catalog_publication_sources)
        .selectinload(CatalogPublicationsSources.source)
        .selectinload(Source.academic)
    )

    publication = db.session.execute(q).scalar_one_or_none()

    if not publication:
        abort(404)

    template = '''
        {% from "ui/_publication_authors.html" import render_publication_authors %}

        {{ render_publication_authors(publication, author_selector) }}
    '''

    return render_template_string(
        template,
        publication=publication,
        author_selector=author_selector,
    )


@blueprint.route("/publication/details/<int:id>/<string:detail_selector>")
def publication_details(id, detail_selector):
    publication = db.get_or_404(Publication, id)

    template = '''
        {% from "ui/publication/_details.html" import render_publication_details %}

        {{ render_publication_details(publication, detail_selector, folders) }}
    '''

    folder_query = Folder.query

    folder_query = folder_query.filter(or_(
        Folder.owner_id == current_user_id(),
        Folder.shared_users.any(User.id == current_user_id()),
    ))

    return render_template_string(
        template,
        publication=publication,
        detail_selector=detail_selector,
        folders=folder_query.all(),
    )


@blueprint.route("/publication/update_preprint/<int:id>/<int:is_preprint>", methods=['POST'])
@roles_accepted('validator')
def publication_update_preprint(id, is_preprint):
    publication = db.get_or_404(Publication, id)
    publication.preprint = is_preprint
    db.session.add(publication)
    db.session.commit()

    return request_publication_bar(publication.id)


@blueprint.route("/publication/update_nihr_acknowledgement/<int:id>/<int:nihr_acknowledgement_id>", methods=['POST'])
@roles_accepted('validator')
def publication_update_nihr_acknowledgement(id, nihr_acknowledgement_id):
    publication = db.get_or_404(Publication, id)

    if nihr_acknowledgement_id == 0:
        publication.nihr_acknowledgement = None
        db.session.commit()
    else:
        publication.nihr_acknowledgement = db.get_or_404(NihrAcknowledgement, nihr_acknowledgement_id)
        db.session.commit()

    return request_publication_bar(publication.id)


def request_publication_bar(publication_id):
    q = select(Publication).where(Publication.id == publication_id)

    q = q.options(
        selectinload(Publication.catalog_publications)
    )

    publication = db.session.execute(q).scalar_one_or_none()

    if not publication:
        abort(404)

    template = '''
        {% from "ui/publication/_details.html" import render_publication_bar %}

        {{ render_publication_bar(publication, current_user, nihr_acknowledgements) }}
    '''

    return render_template_string(
        template,
        publication=publication,
        nihr_acknowledgements=NihrAcknowledgement.query.all(),
    )


@blueprint.route("/publication/<int:id>/supplementary_author/<int:academic_id>/delete", methods=['POST'])
@roles_accepted('editor')
def publication_delete_supplementary_author(id, academic_id):
    publication = db.get_or_404(Publication, id)
    academic = db.get_or_404(Academic, academic_id)

    publication.supplementary_authors.remove(academic)

    db.session.add(publication)
    db.session.commit()

    return trigger_response('refreshAuthors')


@blueprint.route("/publication/<int:id>/supplementary_author/add", methods=['GET', 'POST'])
def publication_add_supplementary_author(id):
    publication = db.get_or_404(Publication, id)

    form = SupplementaryAuthorAddForm(publication=publication)

    if form.validate_on_submit():
        academic = db.get_or_404(Academic, form.academic_id.data)
        publication.supplementary_authors.append(academic)

        db.session.add(publication)
        db.session.commit()

        return trigger_response('refreshAuthors')

    return render_template(
        "lbrc/form_modal.html",
        title='Add Supplementary Author',
        form=form,
        closing_events=['refreshAuthors'],
        submit_label='Add',
        url=url_for('ui.publication_add_supplementary_author', id=id),
    )


