from collections import defaultdict
from datetime import datetime
from pathlib import Path
import shutil
import tempfile
from flask import abort, current_app, jsonify, redirect, render_template, render_template_string, request, send_file, url_for
from flask_security import roles_accepted
from lbrc_flask.database import db
from lbrc_flask.export import excel_download, pdf_download
from lbrc_flask.forms import FlashingForm, MultiCheckboxField
from lbrc_flask.security import current_user_id
from lbrc_flask.response import trigger_response, refresh_response
from weasyprint import HTML
from wtforms import DateField, HiddenField, SelectField, StringField, TextAreaField
from academics.jobs.catalogs import CatalogPublicationRefresh, PublicationReGuessStatus
from academics.model.academic import Academic, AcademicPicker, CatalogPublicationsSources, Source
from academics.model.catalog import CATALOG_MANUAL
from academics.model.folder import Folder, FolderDoi
from academics.model.publication import CatalogPublication, Journal, Keyword, NihrAcknowledgement, Publication, Subtype
from academics.model.security import User
from academics.services.publication_searching import PublicationSearchForm, academic_select_choices, best_catalog_publications, folder_select_choices, journal_select_choices, keyword_select_choices, publication_search_query
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from wtforms.validators import Length, DataRequired, Optional
from werkzeug.utils import secure_filename
from lbrc_flask.requests import get_value_from_all_arguments
from lbrc_flask.async_jobs import AsyncJobs, run_jobs_asynch
from academics.ui.views.folder_dois import add_doi_to_folder
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


class PublicationAddForm(FlashingForm):
    doi = StringField('DOI', validators=[Length(max=50), DataRequired()])
    folder_id = HiddenField('folder_id')
    title = TextAreaField('Title', validators=[Length(max=1000)])
    publication_cover_date = DateField('Publication Cover Date', validators=[Optional()])


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

    publications = db.session.execute(q.order_by(CatalogPublication.publication_period_start)).unique().scalars()

    return pdf_download(
        'ui/publication/publication_export.html',
        publications=publications,
        parameters=search_form.values_description(),
    )


@blueprint.route("/publications/author_report/pdf")
def publication_author_report_pdf():
    search_form = PublicationSearchForm(formdata=request.args)
    
    q = publication_search_query(search_form)
    q = q.options(
        selectinload(Publication.catalog_publications)
        .selectinload(CatalogPublication.catalog_publication_sources)
        .selectinload(CatalogPublicationsSources.source)
        .selectinload(Source.academic)
    )

    publications = db.session.execute(q.order_by(CatalogPublication.publication_period_start)).unique().scalars()

    academics = defaultdict(set)

    for p in publications:
        for a in p.academics:
            academics[a].add(p)

    with tempfile.TemporaryDirectory() as tmpdirname:
        print('created temporary directory', tmpdirname)

        for a, pubs in academics.items():
            html = render_template(
                'ui/publication/publications_by_academic.html',
                publications=pubs,
                academic=a,
                parameters=search_form.values_description(),
            )
            weasy_html = HTML(string=html, base_url=tmpdirname)
            weasy_html.write_pdf(Path(tmpdirname) / secure_filename(a.full_name))

        with tempfile.NamedTemporaryFile(delete=False) as zipfilename:
            zipname = shutil.make_archive(zipfilename.name, 'zip', tmpdirname)
            return send_file(
                zipname,
                as_attachment=True,
                download_name=f'publication_author_report_{datetime.now():%Y%m%d_%H%M%S}.zip',
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


@blueprint.route("/publication/<int:publication_id>/supplementary_author/search")
def publication_supplementary_author_search(publication_id):
    p: Publication = db.get_or_404(Publication, publication_id)

    return render_template(
        "lbrc/search.html",
        title=f"Add Supplementary Author to Publication",
        results_url=url_for('ui.publication_supplementary_author_search_results', publication_id=p.id),
        closing_events=['refreshAuthors'],
    )


@blueprint.route("/publication/<int:publication_id>/supplementary_author/search_results/<int:page>")
@blueprint.route("/publication/<int:publication_id>/supplementary_author/search_results")
def publication_supplementary_author_search_results(publication_id, page=1):
    p: Publication = db.get_or_404(Publication, publication_id)

    search_string: str = get_value_from_all_arguments('search_string') or ''

    q = (
        select(AcademicPicker)
        .where(Academic.id.not_in([a.id for a in p.academics]))
        .where(Academic.id.not_in([a.id for a in p.supplementary_authors]))
        .where((Academic.first_name + ' ' + Academic.last_name).like(f"%{search_string}%"))
        .where(Academic.initialised == 1)
        .order_by(Academic.last_name, Academic.first_name)
    )

    academics = db.paginate(
        select=q,
        page=page,
        per_page=5,
        error_out=False,
    )

    return render_template(
        "lbrc/search_add_results.html",
        add_title="Add academic to publication",
        add_url=url_for('ui.publication_add_supplementary_author', publication_id=p.id),
        results_url='ui.publication_supplementary_author_search_results',
        results_url_args={'publication_id': p.id},
        results=academics,
    )


@blueprint.route("/publication/<int:publication_id>/supplementary_author/add", methods=['GET', 'POST'])
def publication_add_supplementary_author(publication_id):
    p: Publication = db.get_or_404(Publication, publication_id)

    id: int = get_value_from_all_arguments('id')
    a: Academic = db.get_or_404(Academic, id)

    p.supplementary_authors.append(a)

    db.session.add(p)
    db.session.commit()

    return trigger_response('refreshAuthors')


@blueprint.route("/publication/<int:publication_id>/folder/search")
def publication_folder_search(publication_id):
    p: Publication = db.get_or_404(Publication, publication_id)

    return render_template(
        "lbrc/search.html",
        title=f"Add Publication to Folder",
        results_url=url_for('ui.publication_folder_search_results', publication_id=p.id),
        closing_events=['refreshDetails'],
    )


@blueprint.route("/publication/<int:publication_id>/folder/search_results/<int:page>")
@blueprint.route("/publication/<int:publication_id>/folder/search_results")
def publication_folder_search_results(publication_id, page=1):
    p: Publication = db.get_or_404(Publication, publication_id)

    search_string: str = get_value_from_all_arguments('search_string') or ''

    q = (
        select(Folder)
        .where(Folder.id.not_in([a.folder_id for a in p.folder_dois]))
        .where(Folder.name.like(f"%{search_string}%"))
        .order_by(Folder.name)
    )

    academics = db.paginate(
        select=q,
        page=page,
        per_page=5,
        error_out=False,
    )

    return render_template(
        "lbrc/search_add_results.html",
        add_title="Add publication to folder",
        add_url=url_for('ui.publication_add_folder', publication_id=p.id),
        results_url='ui.publication_folder_search_results',
        results_url_args={'publication_id': p.id},
        results=academics,
    )


@blueprint.route("/publication/<int:publication_id>/add_folder", methods=['POST'])
def publication_add_folder(publication_id):
    p: Publication = db.get_or_404(Publication, publication_id)

    id: int = get_value_from_all_arguments('id')
    f: Folder = db.get_or_404(Folder, id)

    add_doi_to_folder(f.id, p.doi)
    db.session.commit()

    return trigger_response('refreshDetails')


@blueprint.route("/catalog_publication/add", methods=['GET', 'POST'])
@blueprint.route("/catalog_publication/<int:id>/edit", methods=['GET', 'POST'])
def catalog_publication_edit(id=None):
    if id:
        catalog_publication = db.get_or_404(CatalogPublication, id)
        form = PublicationAddForm(obj=catalog_publication)
    else:
        catalog_publication = CatalogPublication(catalog=CATALOG_MANUAL)
        form = PublicationAddForm(data=request.args)

    if form.validate_on_submit():
        publication = db.session.execute(
            select(Publication)
            .where(Publication.doi == form.doi.data)
        ).unique().scalar_one_or_none() or Publication(doi=form.doi.data, refresh_full_details=True)

        catalog_publication.catalog_identifier = form.doi.data
        catalog_publication.doi = form.doi.data
        catalog_publication.title = form.title.data or ''
        catalog_publication.publication_cover_date = form.publication_cover_date.data or datetime.now()
        catalog_publication.abstract = ''
        catalog_publication.volume = ''
        catalog_publication.issue = ''
        catalog_publication.pages = ''
        catalog_publication.funding_text = ''
        catalog_publication.href = ''
        catalog_publication.refresh_full_details = True
        catalog_publication.publication = publication

        db.session.add(catalog_publication)
        db.session.flush()

        AsyncJobs.schedule(CatalogPublicationRefresh(catalog_publication))
        db.session.commit()

        if form.has_value('folder_id'):
            add_doi_to_folder(form.folder_id.data, form.doi.data)
            db.session.commit()

        return refresh_response()

    return render_template(
        "lbrc/form_modal.html",
        title='Add Manual Publication' if id is None else 'Edit Manual Publication',
        delete_link=url_for('ui.catalog_publication_delete', id=id) if id is not None else None,
        form=form,
        submit_label='Add' if id is None else 'Save',
        url=url_for('ui.catalog_publication_edit', id=id),
    )


@blueprint.route("/catalog_publication/<int:id>/delete", methods=['POST'])
def catalog_publication_delete(id):
    catalog_publication = db.get_or_404(CatalogPublication, id)

    db.session.delete(catalog_publication)
    db.session.commit()

    return refresh_response()
