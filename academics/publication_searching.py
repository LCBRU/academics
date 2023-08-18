from dateutil.relativedelta import relativedelta
from flask import url_for
from flask_login import current_user
from academics.model import Academic, Folder, Journal, Keyword, NihrAcknowledgement, Objective, ScopusAuthor, ScopusPublication, Subtype, Theme
from lbrc_flask.validators import parse_date_or_none
from sqlalchemy import or_
from wtforms import HiddenField, MonthField, SelectField, SelectMultipleField
from lbrc_flask.forms import SearchForm
from sqlalchemy import func, select


def author_select_choices():
    return [('', '')] + [
        (a.id, f'{a.full_name} ({a.affiliation_name})')
        for a in ScopusAuthor.query.order_by(
            ScopusAuthor.last_name,
            ScopusAuthor.first_name
        ).all()]


def academic_select_choices():
    return [('', '')] + [
        (a.id, f'{a.full_name}')
        for a in Academic.query.order_by(
            Academic.last_name,
            Academic.first_name
        ).all()]


def keyword_select_choices(search_string):
    q = Keyword.query.order_by(Keyword.keyword)

    if search_string:
        for s in search_string.split():
            q = q.filter(Keyword.keyword.like(f'%{s}%'))

    return [(k.id, k.keyword.title()) for k in q.all()]


def journal_select_choices(search_string):
    q = Journal.query.order_by(Journal.name)

    if search_string:
        for s in search_string.split():
            q = q.filter(Journal.name.like(f'%{s}%'))

    return [(j.id, j.name.title()) for j in q.all() if j.name]


def folder_select_choices():
    return [(f.id, f.name.title()) for f in Folder.query.filter(Folder.owner == current_user).order_by(Folder.name).all()]


def objective_select_choices():
    return [(o.id, o.name.title()) for o in Objective.query.order_by(Objective.name).all()]


def nihr_acknowledgement_select_choices():
    return [(f.id, f.name.title()) for f in NihrAcknowledgement.query.order_by(NihrAcknowledgement.name).all()]


class PublicationSearchForm(SearchForm):
    theme_id = SelectField('Theme')
    journal_id = SelectMultipleField('Journal', coerce=int, )
    publication_date_start = MonthField('Publication Start Date')
    publication_date_end = MonthField('Publication End Date')
    subtype_id = SelectMultipleField('Type')
    nihr_acknowledgement_ids = SelectMultipleField('Acknowledgement')
    keywords = SelectMultipleField('Keywords')
    author_id = HiddenField('Author')
    academic_id = SelectField('Academic')
    folder_id = SelectField('Folder')
    objective_id = SelectField('Objective')
    supress_validation_historic = HiddenField('supress_validation_historic')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.journal_id.render_kw={'data-options-href': url_for('ui.publication_journal_options'), 'style': 'width: 300px'}
        self.author_id.choices = author_select_choices()
        self.subtype_id.choices = [('', '')] + [(t.id, t.description) for t in Subtype.query.order_by(Subtype.description).all()]
        self.theme_id.choices = [('', '')] + [(t.id, t.name) for t in Theme.query.all()]
        self.keywords.render_kw={'data-options-href': url_for('ui.publication_keyword_options'), 'style': 'width: 300px'}
        self.folder_id.choices = [('', '')] + folder_select_choices()
        self.objective_id.choices = [('', '')] + objective_select_choices()
        self.nihr_acknowledgement_ids.choices = [('-1', 'Unvalidated')] + nihr_acknowledgement_select_choices()
        self.academic_id.choices = academic_select_choices()


class ValidationSearchForm(SearchForm):
    subtype_id = HiddenField()
    theme_id = SelectField('Theme')
    nihr_acknowledgement_id = SelectField('Acknowledgement', default="-1")
    supress_validation_historic = HiddenField('supress_validation_historic', default=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.nihr_acknowledgement_id.choices = [('0', ''), ('-1', 'Unvalidated')] + nihr_acknowledgement_select_choices()
        self.theme_id.choices = [('0', '')] + [(t.id, t.name) for t in Theme.query.all()]


def publication_search_query(search_form):
    q = select(ScopusPublication)

    if search_form.has_value('author_id'):
        q = q.where(ScopusPublication.scopus_authors.any(ScopusAuthor.id == search_form.author_id.data))

    if search_form.has_value('academic_id'):
        attribution = publication_attribution_query().alias()
        q = q.join(
            attribution, attribution.c.scopus_publication_id == ScopusPublication.id
        ).where(
            attribution.c.academic_id == search_form.academic_id.data
        )

    if search_form.has_value('theme_id'):
        pub_themes = publication_attribution_query().alias()
        q = q.join(pub_themes, pub_themes.c.scopus_publication_id == ScopusPublication.id)
        q = q.where(pub_themes.c.theme_id == search_form.theme_id.data)

    if  search_form.has_value('journal_id'):
        q = q.where(ScopusPublication.journal_id.in_(search_form.journal_id.data))

    if search_form.has_value('subtype_id'):
        q = q.where(ScopusPublication.subtype_id.in_(search_form.subtype_id.data))

    if search_form.has_value('keywords'):
        for k in search_form.keywords.data:
            q = q.where(ScopusPublication.keywords.any(Keyword.id == k))

    if search_form.has_value('publication_date_start'):
        publication_start_date = parse_date_or_none(search_form.publication_date_start.data)
        if publication_start_date:
            q = q.where(ScopusPublication.publication_cover_date >= publication_start_date)

    if search_form.has_value('publication_date_end'):
        publication_end_date = parse_date_or_none(search_form.publication_date_end.data)
        if publication_end_date:
            q = q.where(ScopusPublication.publication_cover_date < (publication_end_date + relativedelta(months=1)))

    if search_form.has_value('search'):
        q = q.where(or_(
            ScopusPublication.title.like(f'%{search_form.search.data}%'),
            ScopusPublication.journal.has(Journal.name.like(f'%{search_form.search.data}%'))
        ))

    acknowledgements = []

    if search_form.has_value('nihr_acknowledgement_ids'):
        acknowledgements = search_form.nihr_acknowledgement_ids.data

    if search_form.has_value('nihr_acknowledgement_id'):
        acknowledgements.append(search_form.nihr_acknowledgement_id.data)

    if acknowledgements:
        status_filter = tuple()

        for ack in acknowledgements:
            if ack == '-1':
                ack = None

            status_filter = (*status_filter, ScopusPublication.nihr_acknowledgement_id == ack)

        q = q.where(or_(*status_filter))

    if search_form.has_value('folder_id'):
        q = q.where(ScopusPublication.folders.any(Folder.id == search_form.folder_id.data))

    if search_form.has_value('objective_id'):
        q = q.where(ScopusPublication.objectives.any(Objective.id == search_form.objective_id.data))

    if search_form.supress_validation_historic.data == True:
        q = q.where(or_(
            ScopusPublication.validation_historic == False,
            ScopusPublication.validation_historic == None,
        ))

    return q


def publication_attribution_query():
    publication_themes = (
        select(
            ScopusPublication.id.label('scopus_publication_id'),
            Theme.id.label('theme_id'),
            Academic.id.label('academic_id'),
            func.row_number().over(partition_by=ScopusPublication.id, order_by=[func.count().desc(), Theme.id]).label('priority')
        )
        .join(ScopusPublication.scopus_authors)
        .join(ScopusAuthor.academic)
        .join(Theme, Theme.id == Academic.theme_id)
        .where(ScopusPublication.subtype_id.in_([s.id for s in Subtype.get_validation_types()]))
        .where(func.coalesce(ScopusPublication.validation_historic, False) == False)
        .group_by(ScopusPublication.id, Theme.id, Theme.name)
        .order_by(ScopusPublication.id, func.count().desc(), Theme.id, Theme.name)
    ).alias()

    return (
        select(
            publication_themes.c.scopus_publication_id,
            publication_themes.c.theme_id,
            publication_themes.c.academic_id,
        )
        .select_from(publication_themes)
        .where(publication_themes.c.priority == 1)
    )
