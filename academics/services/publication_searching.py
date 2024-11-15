from itertools import cycle
import logging
from dateutil.relativedelta import relativedelta
from flask import current_app, url_for
from academics.model.academic import Academic, CatalogPublicationsSources, Source
from academics.model.folder import Folder
from academics.model.group import Group
from academics.model.publication import Journal, Keyword, NihrAcknowledgement, Publication, Subtype, CatalogPublication
from academics.model.catalog import primary_catalogs
from lbrc_flask.validators import parse_date_or_none
from lbrc_flask.data_conversions import ensure_list
from sqlalchemy import case, literal, literal_column, or_
from wtforms import BooleanField, HiddenField, MonthField, SelectField, SelectMultipleField
from lbrc_flask.forms import SearchForm, boolean_coerce
from sqlalchemy import func, select
from lbrc_flask.charting import BarChartItem, SeriesConfig, default_series_colors
from lbrc_flask.database import db
from cachetools import cached, TTLCache
from lbrc_flask.security import current_user_id

from academics.model.security import User
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
    q = select(Folder).where(or_(
        Folder.owner_id == current_user_id(),
        Folder.shared_users.any(User.id == current_user_id()),
    )).order_by(Folder.name)

    return [(f.id, f.name.title()) for f in db.session.execute(q).scalars()]


@cached(cache=TTLCache(maxsize=1, ttl=60))
def group_select_choices():
    q = select(Group).where(or_(
        Group.owner_id == current_user_id(),
        Group.shared_users.any(User.id == current_user_id()),
    )).order_by(Group.name)
    
    return [(g.id, g.name.title()) for g in db.session.execute(q).scalars()]


@cached(cache=TTLCache(maxsize=1, ttl=60))
def nihr_acknowledgement_select_choices():
    return [(f.id, f.name.title()) for f in NihrAcknowledgement.query.order_by(NihrAcknowledgement.name).all()]


class PublicationSearchForm(SearchForm):
    theme_id = SelectField('Theme')
    journal_id = SelectMultipleField('Journal', coerce=int)
    publication_start_month = MonthField('Publication Start Month')
    publication_end_month = MonthField('Publication End Month')
    subtype_id = SelectMultipleField('Type')
    nihr_acknowledgement_ids = SelectMultipleField('Acknowledgements')
    keywords = SelectMultipleField('Keywords')
    author_id = HiddenField('Author')
    academic_id = SelectMultipleField('Academic')
    group_id = SelectField('Group')
    folder_id = SelectField('Folder')
    preprint = SelectField(
        'Preprint',
        choices=[('', ''), ('True', 'Yes'), ('False', 'No')],
        coerce=boolean_coerce,
        default=None,
    )
    supress_validation_historic = BooleanField('Suppress Historic')
    industrial_collaboration = BooleanField('Industrial\nCollabortaion')
    external_collaboration = BooleanField('External\nCollabortaion')

    def __init__(self, **kwargs):
        super().__init__(search_placeholder='Search Title, Journal or DOI', **kwargs)

        self.supress_validation_historic.label.text = f'Suprress Historic\n(before {current_app.config["HISTORIC_PUBLICATION_CUTOFF"]})'
        self.journal_id.render_kw={'data-options-href': url_for('ui.publication_journal_options'), 'style': 'width: 300px'}
        self.subtype_id.choices = [(t.id, t.description) for t in Subtype.query.order_by(Subtype.description).all()]
        self.theme_id.choices = [('', '')] + [(t.id, t.name) for t in Theme.query.all()]
        self.keywords.render_kw={'data-options-href': url_for('ui.publication_keyword_options'), 'style': 'width: 300px'}
        self.folder_id.choices = [('', '')] + folder_select_choices()
        self.nihr_acknowledgement_ids.choices = [('-1', 'Unvalidated')] + nihr_acknowledgement_select_choices()
        self.academic_id.render_kw={'data-options-href': url_for('ui.publication_author_options'), 'style': 'width: 300px'}
        self.group_id.choices = [('', '')] + group_select_choices()


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
        ('type', 'Publication Type'),
        ('external_collaboration', 'External Collaboration'),
        ('industry_collaboration', 'Industrial Collaboration'),
        ('international_collaboration', 'International Collaboration'),
        ('theme_collaboration', 'Theme Collaboration'),
        ('catalog', 'Catalog'),
    ], default='total')
    theme_id = SelectField('Theme')
    group_id = SelectField('Group')
    nihr_acknowledgement_ids = SelectMultipleField('Acknowledgements')
    subtype_id = SelectMultipleField('Type')
    academic_id = HiddenField()
    publication_start_month = MonthField('Publication Start Month')
    publication_end_month = MonthField('Publication End Month')
    supress_validation_historic = BooleanField('Suppress Historic')
    preprint = SelectField(
        'Preprint',
        choices=[('', ''), ('True', 'Yes'), ('False', 'No')],
        coerce=boolean_coerce,
        default=None,
    )

    def __init__(self, **kwargs):
        super().__init__(search_placeholder='Search Title, Journal or DOI', **kwargs)

        self.subtype_id.choices = [(t.id, t.description) for t in Subtype.query.order_by(Subtype.description).all()]
        self.supress_validation_historic.label.text = f'Suprress Historic\n(before {current_app.config["HISTORIC_PUBLICATION_CUTOFF"]})'
        self.theme_id.choices = theme_select_choices()
        self.group_id.choices = group_select_choices()
        self.nihr_acknowledgement_ids.choices = [('-1', 'Unvalidated')] + nihr_acknowledgement_select_choices()
    
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
    supress_validation_historic = HiddenField()


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


def catalog_publication_academics():
    bcp = best_catalog_publications()

    qa = (
        select(CatalogPublicationsSources.catalog_publication_id, Source.academic_id)
        .select_from(CatalogPublicationsSources)
        .join(CatalogPublicationsSources.source)
        .where(Source.academic_id != None)
        .where(CatalogPublicationsSources.catalog_publication_id.in_(bcp))
    )

    qsa = (
        select(CatalogPublication.id, Academic.id)
        .select_from(CatalogPublication)
        .join(CatalogPublication.publication)
        .join(Publication.supplementary_authors)
        .where(CatalogPublication.id.in_(bcp))
    )

    return qa.union(qsa).alias()


def catalog_publication_themes():
    qa = (
        select(CatalogPublicationsSources.catalog_publication_id, Theme.id.label('theme_id'))
        .select_from(CatalogPublicationsSources)
        .join(CatalogPublicationsSources.source)
        .join(Source.academic)
        .join(Academic.themes)
    )

    qsa = (
        select(CatalogPublication.id, Theme.id)
        .select_from(CatalogPublication)
        .join(CatalogPublication.publication)
        .join(Publication.supplementary_authors)
        .join(Academic.themes)
    )

    return qa.union(qsa).alias()


def catalog_publication_groups():
    qa = (
        select(CatalogPublicationsSources.catalog_publication_id, Group.id.label('group_id'))
        .select_from(CatalogPublicationsSources)
        .join(CatalogPublicationsSources.source)
        .join(Source.academic)
        .join(Academic.groups)
    )

    qsa = (
        select(CatalogPublication.id, Group.id)
        .select_from(CatalogPublication)
        .join(CatalogPublication.publication)
        .join(Publication.supplementary_authors)
        .join(Academic.groups)
    )

    return qa.union(qsa).alias()


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

    if search_form.has_value('academic_id'):
        cpa = catalog_publication_academics()

        q = q.where(CatalogPublication.id.in_(
            select(cpa.c.catalog_publication_id)
            .where(cpa.c.academic_id.in_(ensure_list(search_form.academic_id.data))))
        )

    if search_form.has_value('theme_id'):
        cpg = catalog_publication_themes()

        q = q.where(CatalogPublication.id.in_(
            select(cpg.c.catalog_publication_id)
            .where(cpg.c.theme_id.in_(ensure_list(search_form.theme_id.data))))
        )

    if search_form.has_value('group_id'):
        cpg = catalog_publication_groups()

        q = q.where(CatalogPublication.id.in_(
            select(cpg.c.catalog_publication_id)
            .where(cpg.c.group_id.in_(ensure_list(search_form.group_id.data))))
        )

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
        q = q.where(CatalogPublication.publication_period_end >= publication_start_date)

    publication_end_date = None

    if search_form.has_value('publication_end_month'):
        publication_end_date = parse_date_or_none(search_form.publication_end_month.data)

        if publication_end_date:
            publication_end_date += relativedelta(months=1)

    if search_form.has_value('publication_end_date'):
        publication_end_date = parse_date_or_none(search_form.publication_end_date.data)

    if publication_end_date:
        q = q.where(CatalogPublication.publication_period_start < publication_end_date)

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
        q = q.where(CatalogPublication.publication_cover_date >= current_app.config['HISTORIC_PUBLICATION_CUTOFF'])

    if search_form.has_value('preprint'):
        is_is = 1 if search_form.preprint.data else 0
        q = q.where(func.coalesce(Publication.preprint, 0) == is_is)

    if search_form.has_value('industrial_collaboration'):
        is_is = 1 if search_form.industrial_collaboration.data else 0
        q = q.where(Publication.is_industrial_collaboration == is_is)

    if search_form.has_value('international_collaboration'):
        is_is = 1 if search_form.international_collaboration.data else 0
        q = q.where(Publication.is_international_collaboration == is_is)

    if search_form.has_value('external_collaboration'):
        is_is = 1 if search_form.external_collaboration.data else 0
        q = q.where(Publication.is_external_collaboration == is_is)

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
    elif search_form.group_by.data == "type":
        results = by_publication_type(publications)
    elif search_form.group_by.data == "industry_collaboration":
        results = by_industrial_collaboration(publications)
    elif search_form.group_by.data == "international_collaboration":
        results = by_international_collaboration(publications)
    elif search_form.group_by.data == "external_collaboration":
        results = by_external_collaboration(publications)
    elif search_form.group_by.data == "theme_collaboration":
        results = by_theme_collaboration(publications)
    elif search_form.group_by.data == "catalog":
        results = by_catalog(publications)
    else:
        results = by_total(publications)

    return publication_count_value(results)


def all_series_configs(search_form):
    results = []

    cols = iter(cycle(default_series_colors()))

    if search_form.group_by.data == "acknowledgement":
        for a in db.session.execute(select(NihrAcknowledgement)).scalars().all():
            results.append(SeriesConfig(name=a.name, color=a.colour))
    elif search_form.group_by.data == "type":
        for a in db.session.execute(select(Subtype)).scalars().all():
            results.append(SeriesConfig(name=a.description, color=next(cols)))
    elif search_form.group_by.data in ["industry_collaboration", "international_collaboration", "external_collaboration"]:
        results.append(SeriesConfig(name='Collaboration', color=next(cols)))
        results.append(SeriesConfig(name='Not Collaboration', color=next(cols)))
    elif search_form.group_by.data == "theme_collaboration":
        for t, c in zip(db.session.execute(select(Theme.name)).scalars().all(), default_series_colors()):
            results.append(SeriesConfig(name=t, color=c))
    elif search_form.group_by.data == "catalog":
        for t, c in zip(primary_catalogs, default_series_colors()):
            results.append(SeriesConfig(name=t, color=c))
    else:
        results.append(SeriesConfig(name='', color=default_series_colors()[0]))

    return results


def get_publication_by_theme(search_form):
    cat_pubs = catalog_publication_search_query(search_form).alias()

    pub_themes = select(
        CatalogPublication.id,
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
        pub_themes.c.id,
        func.group_concat(pub_themes.c.bucket.distinct().op('ORDER BY pubs.bucket SEPARATOR')(literal_column('" / "'))).label("bucket")
    ).group_by(
        pub_themes.c.id
    ).having(func.count() > 1)

    return multi_theme.union_all(
        select(pub_themes)
    ).cte()


def get_publication_by_academic(search_form):
    cat_pubs = catalog_publication_search_query(search_form).alias()

    q = select(
        CatalogPublication.id,
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
    cat_pubs = catalog_publication_search_query(search_form)

    q = select(
        cat_pubs.c.id,
        literal('brc').label('bucket'),
    )

    return q.cte()


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
        .select_from(CatalogPublication)
        .join(publications, publications.c.id == CatalogPublication.id)
        .join(CatalogPublication.publication)
        .join(NihrAcknowledgement, NihrAcknowledgement.id == Publication.nihr_acknowledgement_id, isouter=True)
        .join(q_total, q_total.c.bucket == publications.c.bucket)
        .group_by(func.coalesce(NihrAcknowledgement.name, 'Unvalidated'), publications.c.bucket)
        .order_by(func.coalesce(NihrAcknowledgement.name, 'Unvalidated'), publications.c.bucket)
    )

    return db.session.execute(q).mappings().all()


def by_publication_type(publications):
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
            Subtype.description.label('series'),
            func.count().label('publications'),
            q_total.c.total_count
        )
        .select_from(CatalogPublication)
        .join(publications, publications.c.id == CatalogPublication.id)
        .join(q_total, q_total.c.bucket == publications.c.bucket)
        .join(CatalogPublication.subtype)
        .group_by(Subtype.description, publications.c.bucket)
        .order_by(Subtype.description, publications.c.bucket)
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

    series_case = case(
        (Publication.is_industrial_collaboration == 1, 'Collaboration'),
        else_='Not Collaboration'
    )

    q = (
        select(
            publications.c.bucket,
            series_case.label('series'),
            func.count().label('publications'),
            q_total.c.total_count
        )
        .select_from(CatalogPublication)
        .join(publications, publications.c.id == CatalogPublication.id)
        .join(CatalogPublication.publication)
        .join(q_total, q_total.c.bucket == publications.c.bucket)
        .group_by(series_case, publications.c.bucket)
        .order_by(series_case, publications.c.bucket)
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

    series_case = case(
        (Publication.is_international_collaboration == 1, 'Collaboration'),
        else_='Not Collaboration'
    )

    q = (
        select(
            publications.c.bucket,
            series_case.label('series'),
            func.count().label('publications'),
            q_total.c.total_count
        )
        .select_from(CatalogPublication)
        .join(publications, publications.c.id == CatalogPublication.id)
        .join(CatalogPublication.publication)
        .join(q_total, q_total.c.bucket == publications.c.bucket)
        .group_by(series_case, publications.c.bucket)
        .order_by(series_case, publications.c.bucket)
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

    series_case = case(
        (Publication.is_external_collaboration == 1, 'Collaboration'),
        else_='Not Collaboration'
    )

    q = (
        select(
            publications.c.bucket,
            series_case.label('series'),
            func.count().label('publications'),
            q_total.c.total_count
        )
        .select_from(CatalogPublication)
        .join(publications, publications.c.id == CatalogPublication.id)
        .join(CatalogPublication.publication)
        .join(q_total, q_total.c.bucket == publications.c.bucket)
        .group_by(series_case, publications.c.bucket)
        .order_by(series_case, publications.c.bucket)
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
        select(CatalogPublication.id, Theme.name.label('theme_name'))
        .select_from(CatalogPublication)
        .join(CatalogPublication.catalog_publication_sources)
        .join(CatalogPublicationsSources.source)
        .join(Source.academic)
        .join(Academic.themes)
        .where(CatalogPublication.id.in_(select(publications.c.id)))
        .group_by(CatalogPublication.id, Theme.name)
    ).alias()

    q = (
        select(
            publications.c.bucket,
            collaboration_theme.c.theme_name.label('series'),
            func.count().label('publications'),
            q_total.c.total_count
        )
        .select_from(publications)
        .join(collaboration_theme, collaboration_theme.c.id == publications.c.id)
        .join(q_total, q_total.c.bucket == publications.c.bucket)
        .group_by(collaboration_theme.c.theme_name, publications.c.bucket)
        .order_by(collaboration_theme.c.id, publications.c.bucket)
    )

    return db.session.execute(q).mappings().all()


def by_catalog(publications):
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
            CatalogPublication.catalog.label('series'),
            func.count().label('publications'),
            q_total.c.total_count
        )
        .select_from(CatalogPublication)
        .join(publications, publications.c.id == CatalogPublication.id)
        .join(q_total, q_total.c.bucket == publications.c.bucket)
        .group_by(CatalogPublication.catalog, publications.c.bucket)
        .order_by(CatalogPublication.catalog, publications.c.bucket)
    )

    return db.session.execute(q).mappings().all()


def by_total(publications):
    q = select(
        publications.c.bucket,
        literal('').label('series'),
        func.count().label('publications'),
        func.count().label('total_count'),
    ).group_by(publications.c.bucket)

    return db.session.execute(q).mappings().all()


def publication_count_value(results):
    return [BarChartItem(
        series=p['series'],
        bucket=p['bucket'],
        count=p['publications']
    ) for p in results]


class PublicationPicker(Publication):
    @property
    def name(self):
        return self.doi


def publication_picker_search_query(search_string: str, exclude_dois: list[str]):
    q = (
        select(PublicationPicker)
        .where(Publication.doi.not_in(exclude_dois))
        .where(Publication.doi.like(f"%{search_string}%"))
        .order_by(Publication.doi)
    )

    return q
