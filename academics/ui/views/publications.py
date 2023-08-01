from flask import abort, jsonify, render_template, request, url_for, redirect, flash
from flask_login import current_user
from flask_security import roles_accepted
from lbrc_flask.forms import SearchForm, FlashingForm
from academics.model import Academic, Folder, Journal, Keyword, NihrAcknowledgement, Objective, ScopusAuthor, ScopusPublication, Subtype, Theme, User
from .. import blueprint
from sqlalchemy import or_
from wtforms import SelectField, MonthField, SelectMultipleField, HiddenField
from lbrc_flask.export import excel_download, pdf_download
from lbrc_flask.validators import parse_date_or_none
from lbrc_flask.json import validate_json
from dateutil.relativedelta import relativedelta
from lbrc_flask.database import db
from lbrc_flask.forms import MultiCheckboxField
from lbrc_flask.security import current_user_id
from academics.scopus.service import auto_validate


def _get_author_choices():
    return [('', '')] + [(a.id, f'{a.full_name} ({a.affiliation_name})') for a in ScopusAuthor.query.order_by(ScopusAuthor.last_name, ScopusAuthor.first_name).all()]


def _get_keyword_choices(search_string):
    q = Keyword.query.order_by(Keyword.keyword)

    if search_string:
        for s in search_string.split():
            q = q.filter(Keyword.keyword.like(f'%{s}%'))

    return [(k.id, k.keyword.title()) for k in q.all()]


def _get_journal_choices(search_string):
    q = Journal.query.order_by(Journal.name)

    if search_string:
        for s in search_string.split():
            q = q.filter(Journal.name.like(f'%{s}%'))

    return [(j.id, j.name.title()) for j in q.all() if j.name]


def _get_folder_choices():
    return [(f.id, f.name.title()) for f in Folder.query.filter(Folder.owner == current_user).order_by(Folder.name).all()]


def _get_objective_choices():
    return [(o.id, o.name.title()) for o in Objective.query.order_by(Objective.name).all()]


def _get_nihr_acknowledgement_choices():
    return [(f.id, f.name.title()) for f in NihrAcknowledgement.query.order_by(NihrAcknowledgement.name).all()]


class PublicationSearchForm(SearchForm):
    theme_id = SelectField('Theme')
    journal_id = SelectMultipleField('Journal', coerce=int, )
    publication_date_start = MonthField('Publication Start Date')
    publication_date_end = MonthField('Publication End Date')
    subtype_id = SelectMultipleField('Type')
    keywords = SelectMultipleField('Keywords')
    author_id = SelectField('Author')
    folder_id = SelectField('Folder')
    objective_id = SelectField('Objective')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.journal_id.render_kw={'data-options-href': url_for('ui.publication_journal_options'), 'style': 'width: 300px'}
        self.author_id.choices = _get_author_choices()
        self.subtype_id.choices = [('', '')] + [(t.id, t.description) for t in Subtype.query.order_by(Subtype.description).all()]
        self.theme_id.choices = [('', '')] + [(t.id, t.name) for t in Theme.query.all()]
        self.keywords.render_kw={'data-options-href': url_for('ui.publication_keyword_options'), 'style': 'width: 300px'}
        self.folder_id.choices = [('', '')] + _get_folder_choices()
        self.objective_id.choices = [('', '')] + _get_objective_choices()


class ValidationSearchForm(SearchForm):
    subtype_id = HiddenField()
    theme_id = SelectField('Theme')
    nihr_acknowledgement_id = SelectField('Acknowledgement', default="-1")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.nihr_acknowledgement_id.choices = [('0', ''), ('-1', 'Unknown')] + _get_nihr_acknowledgement_choices()
        self.theme_id.choices = [('0', '')] + [(t.id, t.name) for t in Theme.query.all()]


class PublicationFolderForm(FlashingForm):
    scopus_publication_id = HiddenField('scopus_publication_id')
    folder_ids = MultiCheckboxField('Folders', coerce=int)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.folder_ids.choices = _get_folder_choices()


@blueprint.route("/publications/")
def publications():
    search_form = PublicationSearchForm(formdata=request.args)
    
    q = _get_publication_query(search_form)

    q = q.order_by(ScopusPublication.publication_cover_date.desc())

    publications = q.paginate(
        page=search_form.page.data,
        per_page=5,
        error_out=False,
    )

    search_form.keywords.choices = [(k.id, k.keyword.title()) for k in Keyword.query.filter(Keyword.id.in_(search_form.keywords.data)).all()]
    search_form.journal_id.choices = [(j.id, j.name.title()) for j in Journal.query.filter(Journal.id.in_(search_form.journal_id.data)).all()]

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
    )


@blueprint.route("/validation/")
@roles_accepted('validator')
def validation():
    search_form = ValidationSearchForm(theme_id=current_user.theme_id, formdata=request.args)
    search_form.subtype_id.data = [s.id for s in Subtype.get_validation_types()]
    
    q = _get_publication_query(search_form, or_status=True, supress_validation_historic=True)

    q = q.order_by(ScopusPublication.publication_cover_date.asc())

    publications = q.paginate(
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
    publication = db.get_or_404(ScopusPublication, request.json.get('id'))

    folder_query = Folder.query.filter(or_(
        Folder.owner_id == current_user_id(),
        Folder.shared_users.any(User.id == current_user_id()),
    ))

    return render_template(
        "ui/publication_folders.html",
        publication=publication,
        folders=folder_query.all(),
    )


def _get_publication_query(search_form, or_status=False, supress_validation_historic=False):
    q = ScopusPublication.query

    if search_form.has_value('author_id'):
        q = q.filter(ScopusPublication.scopus_authors.any(ScopusAuthor.id == search_form.author_id.data))

    if search_form.has_value('theme_id'):
        aq = ScopusAuthor.query.with_entities(ScopusAuthor.id.distinct())
        aq = aq.join(ScopusAuthor.academic)
        aq = aq.filter(Academic.theme_id == search_form.theme_id.data)
        aq = aq.subquery()

        q = q.filter(ScopusPublication.scopus_authors.any(ScopusAuthor.id.in_(aq)))

    if  search_form.has_value('journal_id'):
        q = q.filter(ScopusPublication.journal_id.in_(search_form.journal_id.data))

    if search_form.has_value('subtype_id'):
        q = q.filter(ScopusPublication.subtype_id.in_(search_form.subtype_id.data))

    if search_form.has_value('keywords'):
        for k in search_form.keywords.data:
            q = q.filter(ScopusPublication.keywords.any(Keyword.id == k))

    if search_form.has_value('publication_date_start'):
        publication_start_date = parse_date_or_none(search_form.publication_date_start.data)
        if publication_start_date:
            q = q.filter(ScopusPublication.publication_cover_date >= publication_start_date)

    if search_form.has_value('publication_date_end'):
        publication_end_date = parse_date_or_none(search_form.publication_date_end.data)
        if publication_end_date:
            q = q.filter(ScopusPublication.publication_cover_date < (publication_end_date + relativedelta(months=1)))

    if search_form.has_value('search'):
        q = q.filter(or_(
            ScopusPublication.title.like(f'%{search_form.search.data}%'),
            ScopusPublication.journal.has(Journal.name.like(f'%{search_form.search.data}%'))
        ))

    status_filter = tuple()

    if search_form.has_value('nihr_acknowledgement_id'):
        nihr_acknowledgement_id = search_form.nihr_acknowledgement_id.data

        if nihr_acknowledgement_id == '-1':
            nihr_acknowledgement_id = None

        status_filter = (*status_filter, ScopusPublication.nihr_acknowledgement_id == nihr_acknowledgement_id)

    if or_status:
        q = q.filter(or_(*status_filter))
    else:
        q = q.filter(*status_filter)

    if search_form.has_value('folder_id'):
        q = q.filter(ScopusPublication.folders.any(Folder.id == search_form.folder_id.data))

    if search_form.has_value('objective_id'):
        q = q.filter(ScopusPublication.objectives.any(Objective.id == search_form.objective_id.data))

    if supress_validation_historic:
        q = q.filter(or_(
            ScopusPublication.validation_historic == False,
            ScopusPublication.validation_historic == None,
        ))

    return q


@blueprint.route("/publications/export/xslt")
def publication_full_export_xlsx():
    # Use of dictionary instead of set to maintain order of headers
    headers = {
        'scopus_id': None,
        'doi': None,
        'pubmed_id': None,
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
        'funding acronym': None,
    }

    search_form = PublicationSearchForm(formdata=request.args)
    
    q = _get_publication_query(search_form)

    q = q.order_by(ScopusPublication.publication_cover_date.desc())

    publication_details = ({
        'scopus_id': p.scopus_id,
        'doi': p.doi,
        'pubmed_id': p.pubmed_id,
        'journal': p.journal.name if p.journal else '',
        'type': p.subtype.description if p.subtype else '',
        'volume': p.volume,
        'issue': p.issue,
        'pages': p.pages,
        'publication_cover_date': p.publication_cover_date,
        'authors': p.author_list,
        'title': p.title,
        'abstract': p.abstract,
        'open access': p.is_open_access,
        'citations': p.cited_by_count,
        'sponsor': '; '.join([s.name for s in p.sponsors]),
    } for p in q.all())

    return excel_download('Academics_Publications', headers.keys(), publication_details)


@blueprint.route("/publications/export/annual_report")
def publication_full_annual_report_xlsx():
    # Use of dictionary instead of set to maintain order of headers
    headers = {
        'Publication Reference': None,
        'DOI': None,
    }

    search_form = PublicationSearchForm(formdata=request.args)
    
    q = _get_publication_query(search_form)

    q = q.order_by(ScopusPublication.publication_cover_date.desc())

    publication_details = ({
        'Publication Reference': p.vancouverish,
        'DOI': p.doi,
    } for p in q.all())

    return excel_download('Academics_Publications', headers.keys(), publication_details)


@blueprint.route("/publications/export/pdf")
def publication_export_pdf():
    search_form = PublicationSearchForm(formdata=request.args)
    
    q = _get_publication_query(search_form)

    parameters = []

    if search_form.author_id.data:
        author = db.get_or_404(ScopusAuthor, search_form.author_id.data)
        parameters.append(('Author', author.full_name))

    if search_form.theme_id.data:
        theme = db.get_or_404(Theme, search_form.theme_id.data)
        parameters.append(('Theme', theme.name))

    publication_start_date = parse_date_or_none(search_form.publication_date_start.data)
    if publication_start_date:
        parameters.append(('Start Publication Date', f'{publication_start_date:%b %Y}'))

    publication_end_date = parse_date_or_none(search_form.publication_date_end.data)
    if publication_end_date:
        parameters.append(('End Publication Date', f'{publication_end_date:%b %Y}'))

    if q.count() > 100:
        abort(413)

    publications = q.order_by(ScopusPublication.publication_cover_date.desc()).all()

    return pdf_download('ui/publications_pdf.html', title='Academics Publications', publications=publications, parameters=parameters)


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
    p = db.get_or_404(ScopusPublication, request.json.get('id'))

    if request.json.get('nihr_acknowledgement_id') == -1:
        p.nihr_acknowledgement = None
        db.session.commit()

        return jsonify({'status': 'Unknown'}), 200
    else:
        n = db.get_or_404(NihrAcknowledgement, request.json.get('nihr_acknowledgement_id'))

        p.nihr_acknowledgement = n

        db.session.commit()

        return jsonify({'status': n.name}), 200


@blueprint.route("/publication/keywords/options")
def publication_keyword_options():
    return jsonify({'results': [{'id': id, 'text': text} for id, text in _get_keyword_choices(request.args.get('q'))]})


@blueprint.route("/publication/journal/options")
def publication_journal_options():
    return jsonify({'results': [{'id': id, 'text': text} for id, text in _get_journal_choices(request.args.get('q'))]})


@blueprint.route("/publication/auto_validate")
def publication_auto_validate():
    amended_count = auto_validate()
    flash(f'{amended_count} record(s) automatically updated')
    return redirect(url_for('ui.index'))