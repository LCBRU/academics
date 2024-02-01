import logging
from dateutil.relativedelta import relativedelta
from flask import url_for
from flask_login import current_user
from academics.model.academic import Academic, Affiliation, CatalogPublicationsSources, Source
from academics.model.folder import Folder
from academics.model.publication import Journal, Keyword, NihrAcknowledgement, Publication, Subtype, CatalogPublication
from lbrc_flask.validators import parse_date_or_none
from lbrc_flask.data_conversions import ensure_list
from sqlalchemy import case, distinct, literal, literal_column, or_
from wtforms import HiddenField, MonthField, SelectField, SelectMultipleField
from lbrc_flask.forms import SearchForm, boolean_coerce
from sqlalchemy import func, select
from lbrc_flask.charting import BarChartItem
from lbrc_flask.database import db
from cachetools import cached, TTLCache

from academics.model.theme import Theme


@cached(cache=TTLCache(maxsize=1, ttl=60))
def theme_select_choices():
    return [('', '')] + [(t.id, t.name) for t in Theme.query.all()]


@cached(cache=TTLCache(maxsize=1, ttl=60))
def academic_select_choices(search_string=None):
    q = (
        select(Academic)
        .where(Academic.initialised == True)
        .order_by(Academic.last_name, Academic.first_name)
    )

    if search_string:
        q = q.filter((Academic.first_name + ' ' + Academic.last_name).like("%{}%".format(search_string)))

    return [
        (a.id, f'{a.full_name}')
        for a in db.session.execute(q).scalars()
    ]


@cached(cache=TTLCache(maxsize=1, ttl=60))
def keyword_select_choices(search_string):
    q = Keyword.query.order_by(Keyword.keyword)

    if search_string:
        for s in search_string.split():
            q = q.filter(Keyword.keyword.like(f'%{s}%'))

    return [(k.id, k.keyword.title()) for k in q.all()]


@cached(cache=TTLCache(maxsize=1, ttl=60))
def journal_select_choices(search_string):
    q = Journal.query.order_by(Journal.name)

    if search_string:
        for s in search_string.split():
            q = q.filter(Journal.name.like(f'%{s}%'))

    return [(j.id, j.name.title()) for j in q.all() if j.name]


@cached(cache=TTLCache(maxsize=1, ttl=60))
def folder_select_choices():
    return [(f.id, f.name.title()) for f in Folder.query.filter(Folder.owner == current_user).order_by(Folder.name).all()]


@cached(cache=TTLCache(maxsize=1, ttl=60))
def nihr_acknowledgement_select_choices():
    return [(f.id, f.name.title()) for f in NihrAcknowledgement.query.order_by(NihrAcknowledgement.name).all()]


class PublicationSearchForm(SearchForm):
    theme_id = SelectField('Theme')
    journal_id = SelectMultipleField('Journal', coerce=int, )
    publication_start_month = MonthField('Publication Start Month')
    publication_end_month = MonthField('Publication End Month')
    subtype_id = SelectMultipleField('Type')
    nihr_acknowledgement_ids = SelectMultipleField('Acknowledgement')
    keywords = SelectMultipleField('Keywords')
    author_id = HiddenField('Author')
    academic_id = SelectMultipleField('Academic')
    folder_id = SelectField('Folder')
    supress_validation_historic = SelectField(
        'Suppress Historic',
        choices=[(True, 'Yes'), (False, 'No')],
        coerce=lambda x: x == 'True',
        default='False',
    )
    industrial_collaboration = SelectField(
        'Industrial Collabortaion',
        choices=[('', ''), ('True', 'Yes'), ('False', 'No')],
        coerce=boolean_coerce,
        default=None,
    )
    international_collaboration = SelectField(
        'International Collabortaion',
        choices=[('', ''), ('True', 'Yes'), ('False', 'No')],
        coerce=boolean_coerce,
        default=None,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.journal_id.render_kw={'data-options-href': url_for('ui.publication_journal_options'), 'style': 'width: 300px'}
        self.subtype_id.choices = [(t.id, t.description) for t in Subtype.query.order_by(Subtype.description).all()]
        self.theme_id.choices = [('', '')] + [(t.id, t.name) for t in Theme.query.all()]
        self.keywords.render_kw={'data-options-href': url_for('ui.publication_keyword_options'), 'style': 'width: 300px'}
        self.folder_id.choices = [('', '')] + folder_select_choices()
        self.nihr_acknowledgement_ids.choices = [('-1', 'Unvalidated')] + nihr_acknowledgement_select_choices()
        self.academic_id.render_kw={'data-options-href': url_for('ui.publication_author_options'), 'style': 'width: 300px'}


class PublicationSummarySearchForm(SearchForm):
    SUMMARY_TYPE__ACADEMIC = 'ACADEMIC'
    SUMMARY_TYPE__THEME = 'THEME'
    SUMMARY_TYPE__BRC = 'BRC'

    total = SelectField('Total By', choices=[
        (SUMMARY_TYPE__BRC, 'BRC'),
        (SUMMARY_TYPE__THEME, 'Theme'),
        (SUMMARY_TYPE__ACADEMIC, 'Academic')
    ], default='BRC')
    group_by = SelectField('Group By', choices=[
        ('total', 'Total'),
        ('acknowledgement', 'Acknowledgement Status'),
        ('external_collaboration', 'External Collaboration'),
        ('industry_collaboration', 'Industrial Collaboration'),
        ('international_collaboration', 'International Collaboration'),
        ('theme_collaboration', 'Theme Collaboration'),
    ], default='total')
    measure = SelectField('Measure', choices=[('percentage', 'Percentage'), ('publications', 'Publications')], default='publications')
    theme_id = SelectField('Theme')
    nihr_acknowledgement_id = SelectMultipleField('Acknowledgement')
    academic_id = HiddenField()
    publication_start_month = MonthField('Publication Start Month')
    publication_end_date = MonthField('Publication End Month')
    supress_validation_historic = SelectField(
        'Suppress Historic',
        choices=[(True, 'Yes'), (False, 'No')],
        coerce=lambda x: x == 'True',
        default='True',
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.theme_id.choices = theme_select_choices()
        self.nihr_acknowledgement_id.choices = [('-1', 'Unvalidated')] + nihr_acknowledgement_select_choices()
    
    @property
    def summary_type(self):
        if self.has_value('academic_id') or self.total.data == self.SUMMARY_TYPE__ACADEMIC:
            return self.SUMMARY_TYPE__ACADEMIC
        elif self.has_value('theme_id') or self.total.data == self.SUMMARY_TYPE__THEME:
            return self.SUMMARY_TYPE__THEME
        else:
            return self.SUMMARY_TYPE__BRC


class ValidationSearchForm(SearchForm):
    subtype_id = HiddenField()
    theme_id = SelectField('Theme')
    nihr_acknowledgement_id = SelectField('Acknowledgement', default="-1")
    supress_validation_historic = SelectField(
        'Suppress Historic',
        choices=[(True, 'Yes'), (False, 'No')],
        coerce=lambda x: x == 'True',
        default='True',
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.nihr_acknowledgement_id.choices = [('0', ''), ('-1', 'Unvalidated')] + nihr_acknowledgement_select_choices()
        self.theme_id.choices = [('0', '')] + [(t.id, t.name) for t in Theme.query.all()]


def best_catalog_publications():
    catalog_publications = (
        select(
            CatalogPublication.id,
            func.row_number().over(partition_by=CatalogPublication.publication_id, order_by=[CatalogPublication.catalog.desc()]).label('priority')
        )
    ).alias()

    return (
        select(catalog_publications.c.id)
        .select_from(catalog_publications)
        .where(catalog_publications.c.priority == 1)
    )


def publication_search_query(search_form):
    cat_pubs = catalog_publication_search_query(search_form)

    q = (
        select(Publication)
        .select_from(cat_pubs)
        .join(CatalogPublication, CatalogPublication.id == cat_pubs.c.id)
        .join(CatalogPublication.publication)
        .distinct()
    )

    return q


def catalog_publication_search_query(search_form):
    logging.debug(f'publication_search_query started')

    bcp = best_catalog_publications()

    q = select(CatalogPublication.id).join(CatalogPublication.publication).where(CatalogPublication.id.in_(bcp))

    if search_form.has_value('author_id'):
        q = q.where(CatalogPublication.catalog_publication_sources.any(
            CatalogPublicationsSources.source_id == search_form.author_id.data
        ))

    print('academic_id')
    if search_form.has_value('academic_id'):
        q = q.where(CatalogPublication.id.in_(
            select(CatalogPublicationsSources.catalog_publication_id)
            .join(CatalogPublicationsSources.source)
            .where(Source.academic_id.in_(ensure_list(search_form.academic_id.data)))
        ))

    if search_form.has_value('theme_id'):
        q = q.where(CatalogPublication.id.in_(
            select(CatalogPublicationsSources.catalog_publication_id)
            .join(CatalogPublicationsSources.source)
            .join(Source.academic)
            .where(Academic.themes.any(Theme.id == search_form.theme_id.data))
        ))

    if  search_form.has_value('journal_id'):
        q = q.where(CatalogPublication.journal_id.in_(search_form.journal_id.data))

    if search_form.has_value('subtype_id'):
        q = q.where(CatalogPublication.subtype_id.in_(search_form.subtype_id.data))

    if search_form.has_value('keywords'):
        for k in search_form.keywords.data:
            q = q.where(CatalogPublication.keywords.any(Keyword.id == k))

    publication_start_date = None

    if search_form.has_value('publication_start_month'):
        publication_start_date = parse_date_or_none(search_form.publication_start_month.data)

    if search_form.has_value('publication_start_date'):
        publication_start_date = parse_date_or_none(search_form.publication_start_date.data)

    if publication_start_date:
        q = q.where(CatalogPublication.publication_cover_date >= publication_start_date)

    publication_end_date = None

    if search_form.has_value('publication_end_month'):
        publication_end_date = parse_date_or_none(search_form.publication_end_month.data)

    if search_form.has_value('publication_end_date'):
        publication_end_date = parse_date_or_none(search_form.publication_end_date.data)

    if publication_end_date:
        q = q.where(CatalogPublication.publication_cover_date < (publication_end_date + relativedelta(months=1)))

    if search_form.has_value('search'):
        q = q.where(or_(
            CatalogPublication.title.like(f'%{search_form.search.data}%'),
            CatalogPublication.journal.has(Journal.name.like(f'%{search_form.search.data}%')),
            CatalogPublication.doi.like(f'%{search_form.search.data}%'),
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

            status_filter = (*status_filter, Publication.nihr_acknowledgement_id == ack)

        q = q.where(or_(*status_filter))

    if search_form.has_value('folder_id'):
        q = q.where(Publication.folders.any(Folder.id == search_form.folder_id.data))

    if search_form.supress_validation_historic.data == True:
        logging.debug(f'Supressing Historic Publications')
        q = q.where(or_(
            Publication.validation_historic == False,
            Publication.validation_historic == None,
        ))

    if search_form.has_value('industrial_collaboration'):
        is_is = 1 if search_form.industrial_collaboration.data else 0
        q = q.where(Publication.is_industrial_collaboration == is_is)

    if search_form.has_value('international_collaboration'):
        is_is = 1 if search_form.industrial_collaboration.data else 0
        q = q.where(Publication.is_international_collaboration == is_is)

    logging.debug(f'publication_search_query ended')

    return q


def publication_count(search_form):
    pubs = catalog_publication_search_query(search_form).alias()
    q = select(func.count()).select_from(pubs)
    return db.session.execute(q).scalar()


def publication_summary(search_form):
    if search_form.summary_type == search_form.SUMMARY_TYPE__ACADEMIC:
        publications = get_publication_by_academic(search_form)
    elif search_form.summary_type == search_form.SUMMARY_TYPE__THEME:
        publications = get_publication_by_theme(search_form)
    else:
        publications = get_publication_by_brc(search_form)

    if search_form.group_by.data == "acknowledgement":
        results = by_acknowledge_status(publications)
    elif search_form.group_by.data == "industry_collaboration":
        results = by_industrial_collaboration(publications)
    elif search_form.group_by.data == "international_collaboration":
        results = by_international_collaboration(publications)
    elif search_form.group_by.data == "external_collaboration":
        results = by_external_collaboration(publications)
    elif search_form.group_by.data == "theme_collaboration":
        results = by_theme_collaboration(publications)
    else:
        results = by_total(publications)

    if search_form.measure.data == 'publications':
        items = publication_count_value(results)
    else:
        items = percentage_value(results)

    return items


def get_publication_by_theme(search_form):
    cat_pubs = catalog_publication_search_query(search_form).alias()

    pub_themes = select(
        CatalogPublication.publication_id,
        Theme.name.label('bucket')
    ).select_from(
        cat_pubs
    ).join(
        CatalogPublication, CatalogPublication.id == cat_pubs.c.id
    ).join(
        CatalogPublication.catalog_publication_sources
    ).join(
        CatalogPublicationsSources.source
    ).join(
        Source.academic
    ).join(
        Academic.themes
    ).distinct()

    if search_form.has_value('theme_id'):
        pub_themes = pub_themes.where(Theme.id == search_form.theme_id.data)

    pub_themes = pub_themes.cte('pubs')

    multi_theme = select(
        pub_themes.c.publication_id,
        func.group_concat(pub_themes.c.bucket.distinct().op('ORDER BY pubs.bucket SEPARATOR')(literal_column('" / "'))).label("bucket")
    ).group_by(
        pub_themes.c.publication_id
    ).having(func.count() > 1)

    return multi_theme.union_all(
        select(pub_themes)
    ).cte()


def get_publication_by_academic(search_form):
    cat_pubs = catalog_publication_search_query(search_form).alias()

    q = select(
        CatalogPublication.publication_id,
        func.concat(Academic.first_name, ' ', Academic.last_name).label('bucket')
    ).select_from(
        cat_pubs
    ).join(
        CatalogPublication, CatalogPublication.id == cat_pubs.c.id
    ).join(
        CatalogPublication.catalog_publication_sources
    ).join(
        CatalogPublicationsSources.source
    ).join(
        Source.academic
    ).distinct().order_by(
        Academic.last_name,
        Academic.first_name,
    )

    if search_form.has_value('academic_id'):
        q = q.where(Academic.id == search_form.academic_id.data)
    
    return q.cte()


def get_publication_by_brc(search_form):
    cat_pubs = catalog_publication_search_query(search_form).alias()

    return select(
        CatalogPublication.publication_id,
        literal('brc').label('bucket')
    ).where(CatalogPublication.id.in_(cat_pubs)).cte()


def by_acknowledge_status(publications):
    q_total = (
        select(
            publications.c.bucket,
            func.count().label('total_count'),
        )
        .group_by(publications.c.bucket)
    ).alias()

    q = (
        select(
            publications.c.bucket,
            func.coalesce(NihrAcknowledgement.name, 'Unvalidated').label('series'),
            func.count().label('publications'),
            q_total.c.total_count
        )
        .select_from(Publication)
        .join(publications, publications.c.publication_id == Publication.id)
        .join(NihrAcknowledgement, NihrAcknowledgement.id == Publication.nihr_acknowledgement_id, isouter=True)
        .join(q_total, q_total.c.bucket == publications.c.bucket)
        .group_by(func.coalesce(NihrAcknowledgement.name, 'Unvalidated'), publications.c.bucket)
        .order_by(func.coalesce(NihrAcknowledgement.name, 'Unvalidated'), publications.c.bucket)
    )

    return db.session.execute(q).mappings().all()


def by_industrial_collaboration(publications):
    q_total = (
        select(
            publications.c.bucket,
            func.count().label('total_count'),
        )
        .group_by(publications.c.bucket)
    ).alias()

    industry = (
        select(distinct(CatalogPublication.publication_id).label("publication_id"))
        .select_from(CatalogPublication)
        .join(CatalogPublication.catalog_publication_sources)
        .join(CatalogPublicationsSources.affiliations)
        .where(Affiliation.industry == True)
        .where(CatalogPublication.publication_id.in_(select(publications.c.publication_id)))
    ).alias()

    series_case = case(
        (industry.c.publication_id == None, 'Not Collaboration'),
        else_='Collaboration'
    )

    q = (
        select(
            publications.c.bucket,
            series_case.label('series'),
            func.count().label('publications'),
            q_total.c.total_count
        )
        .select_from(publications)
        .join(industry, industry.c.publication_id == publications.c.publication_id, isouter=True)
        .join(q_total, q_total.c.bucket == publications.c.bucket)
        .group_by(series_case, publications.c.bucket)
        .order_by(industry.c.publication_id, publications.c.bucket)
    )

    return db.session.execute(q).mappings().all()


def by_international_collaboration(publications):
    q_total = (
        select(
            publications.c.bucket,
            func.count().label('total_count'),
        )
        .group_by(publications.c.bucket)
    ).alias()

    international = (
        select(distinct(CatalogPublication.publication_id).label("publication_id"))
        .select_from(CatalogPublication)
        .join(CatalogPublication.catalog_publication_sources)
        .join(CatalogPublicationsSources.affiliations)
        .where(Affiliation.international == True)
        .where(CatalogPublication.publication_id.in_(select(publications.c.publication_id)))
    ).alias()

    series_case = case(
        (international.c.publication_id == None, 'Not Collaboration'),
        else_='Collaboration'
    )

    q = (
        select(
            publications.c.bucket,
            series_case.label('series'),
            func.count().label('publications'),
            q_total.c.total_count
        )
        .select_from(publications)
        .join(international, international.c.publication_id == publications.c.publication_id, isouter=True)
        .join(q_total, q_total.c.bucket == publications.c.bucket)
        .group_by(series_case, publications.c.bucket)
        .order_by(international.c.publication_id, publications.c.bucket)
    )

    return db.session.execute(q).mappings().all()


def by_external_collaboration(publications):
    q_total = (
        select(
            publications.c.bucket,
            func.count().label('total_count'),
        )
        .group_by(publications.c.bucket)
    ).alias()

    not_collaboration = (
        select(distinct(CatalogPublication.publication_id).label("publication_id"))
        .select_from(CatalogPublication)
        .join(CatalogPublication.catalog_publication_sources)
        .join(CatalogPublicationsSources.affiliations)
        .where(Affiliation.home_organisation == True)
        .where(CatalogPublication.publication_id.in_(select(publications.c.publication_id)))
    ).alias()

    series_case = case(
        (not_collaboration.c.publication_id == None, 'Collaboration'),
        else_='Not Collaboration'
    )

    q = (
        select(
            publications.c.bucket,
            series_case.label('series'),
            func.count().label('publications'),
            q_total.c.total_count
        )
        .select_from(publications)
        .join(not_collaboration, not_collaboration.c.publication_id == publications.c.publication_id, isouter=True)
        .join(q_total, q_total.c.bucket == publications.c.bucket)
        .group_by(series_case, publications.c.bucket)
        .order_by(not_collaboration.c.publication_id, publications.c.bucket)
    )

    return db.session.execute(q).mappings().all()


def by_theme_collaboration(publications):
    q_total = (
        select(
            publications.c.bucket,
            func.count().label('total_count'),
        )
        .group_by(publications.c.bucket)
    ).alias()

    collaboration_theme = (
        select(CatalogPublication.publication_id, Theme.name.label('theme_name'))
        .select_from(CatalogPublication)
        .join(CatalogPublication.catalog_publication_sources)
        .join(CatalogPublicationsSources.source)
        .join(Source.academic)
        .join(Academic.themes)
        .where(CatalogPublication.publication_id.in_(select(publications.c.publication_id)))
        .group_by(CatalogPublication.publication_id, Theme.name)
    ).alias()

    q = (
        select(
            publications.c.bucket,
            collaboration_theme.c.theme_name.label('series'),
            func.count().label('publications'),
            q_total.c.total_count
        )
        .select_from(publications)
        .join(collaboration_theme, collaboration_theme.c.publication_id == publications.c.publication_id)
        .join(q_total, q_total.c.bucket == publications.c.bucket)
        .group_by(collaboration_theme.c.theme_name, publications.c.bucket)
        .order_by(collaboration_theme.c.publication_id, publications.c.bucket)
    )

    return db.session.execute(q).mappings().all()


def by_total(publications):
    q = (
        select(
            publications.c.bucket,
            literal('').label('series'),
            func.count().label('publications'),
            func.count().label('total_count'),
        )
        .group_by(publications.c.bucket)
    )

    return db.session.execute(q).mappings().all()


def publication_count_value(results):
    return [BarChartItem(
        series=p['series'],
        bucket=p['bucket'],
        count=p['publications']
    ) for p in results]


def percentage_value(results):
    return [BarChartItem(
        series=p['series'],
        bucket=p['bucket'],
        count=round(p['publications'] * 100 / p['total_count'])
    ) for p in results]
