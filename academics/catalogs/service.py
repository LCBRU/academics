from itertools import chain, groupby
import logging
from pathlib import Path
from flask import current_app
from sqlalchemy import delete, or_, select, update
from academics.catalogs.open_alex import get_open_alex_affiliation_data, get_open_alex_author_data, get_open_alex_publication_data, get_openalex_publications, open_alex_similar_authors
from academics.catalogs.scopus import get_scopus_affiliation_data, get_scopus_author_data, get_scopus_publication_data, get_scopus_publications, scopus_similar_authors
from academics.catalogs.scival import get_scival_institution, get_scival_publication_institutions
from academics.catalogs.data_classes import CatalogReference, _affiliation_xref_for_author_data_list, _institutions, _journal_xref_for_publication_data_list, _keyword_xref_for_publication_data_list, _publication_xref_for_publication_data_list, _source_xref_for_author_data_list, _source_xref_for_publication_data_list, _sponsor_xref_for_publication_data_list, _subtype_xref_for_publication_data_list
from academics.model.academic import Academic, AcademicPotentialSource, Affiliation, CatalogPublicationsSources, Source, catalog_publications_sources_affiliations
from academics.model.catalog import CATALOG_SCIVAL
from academics.model.publication import CATALOG_OPEN_ALEX, CATALOG_SCOPUS, CatalogPublication, NihrAcknowledgement, Publication
from academics.model.folder import FolderDoi
from academics.model.institutions import Institution
from lbrc_flask.celery import celery
from celery.signals import after_setup_logger
from lbrc_flask.database import db
from datetime import date, datetime
from lbrc_flask.logging import log_exception
from lbrc_flask.validators import parse_date
from academics.model.raw_data import RawData
from dateutil.relativedelta import relativedelta


@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    formatter = logging.Formatter('%(asctime)s (%(levelname)s) %(module)s::%(funcName)s(%(lineno)d): %(message)s')

    # add filehandler
    fh = logging.FileHandler(str(Path(current_app.config["CELERY_LOG_DIRECTORY"]) / 'service.log'))
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.propagate = False


def updating():
    result = Academic.query.filter(Academic.updating == True).count() > 0
    logging.info(result)
    return result


def refresh():
    logging.debug('started')

    _process_updates.delay()

    logging.debug('ended')


def add_sources_to_academic(catalog, catalog_identifiers, academic_id=None, themes=None):
    academic = None

    if academic_id:
        academic = db.session.get(Academic, academic_id)

    if not academic:
        academic = Academic()
        academic.themes = themes
    
    academic.updating = True

    db.session.add(academic)

    sources = [
        get_or_create_source(catalog=catalog, catalog_identifier=ci)
        for ci in catalog_identifiers
    ]

    create_potential_sources(sources, academic, not_match=False)

    db.session.commit()

    _process_updates.delay()


def create_potential_sources(sources, academic, not_match=True):
    existing_sources = {CatalogReference(s.source) for s in db.session.execute(
        select(AcademicPotentialSource)
        .where(AcademicPotentialSource.academic == academic)
    ).scalars()}

    for s in sources:
        s.academic = academic

    potentials = [
        AcademicPotentialSource(academic=academic, source=s, not_match=not_match)
        for s in sources
        if CatalogReference(s) not in existing_sources
    ]

    db.session.add_all(sources)
    db.session.add_all(potentials)
    db.session.commit()


def get_or_create_source(catalog, catalog_identifier):
    result = db.session.execute(
        select(Source)
        .where(Source.catalog == catalog)
        .where(Source.catalog_identifier == catalog_identifier)
    ).unique().scalar()

    if not result:
        result = Source(
            catalog=catalog,
            catalog_identifier=catalog_identifier,
        )

    return result


def update_single_academic(academic: Academic):
    logging.debug('started')

    academic.mark_for_update()

    db.session.add(academic)
    db.session.commit()

    _process_updates.delay()

    logging.debug('ended')


def update_academics():
    logging.debug('started')
    if not updating():
        for academic in Academic.query.all():
            logging.debug(f'Setting academic {academic.full_name} to be updated')

            academic.mark_for_update()

            db.session.add(academic)

        db.session.commit()

        _process_updates.delay()

    logging.debug('ended')


@celery.task()
def _process_updates():
    logging.debug('started')

    refresh_Academics()
    refresh_catalog_publications()
    refresh_publications()
    remove_publication_without_catalog_entry()
    refresh_affiliations()
    refresh_institutions()

    logging.debug('Ended')


def refresh_affiliations():
    logging.debug('started')

    while True:
        a = Affiliation.query.filter(Affiliation.refresh_details == 1).first()

        if not a:
            logging.info('No more affiliations to refresh')
            break

        _update_affiliation(a)

    logging.debug('ended')


def refresh_institutions():
    logging.debug('started')

    while True:
        i = Institution.query.filter(Institution.refresh_full_details == 1).first()

        if not i:
            logging.info('No more institutions to refresh')
            break

        _update_institution(i)

    logging.debug('ended')


def _update_affiliation(affiliation: Affiliation):
    logging.debug(affiliation.line_summary)

    try:
        if affiliation.catalog == CATALOG_SCOPUS:
            aff_data = get_scopus_affiliation_data(affiliation.catalog_identifier)
        if affiliation.catalog == CATALOG_OPEN_ALEX:
            aff_data = get_open_alex_affiliation_data(affiliation.catalog_identifier)

        aff_data.update_affiliation(affiliation)

        affiliation.refresh_details = False

        db.session.add(affiliation)
        db.session.commit()

    except Exception as e:
        log_exception(e)

        logging.warn('Rolling back transaction')

        db.session.rollback()
        db.session.execute(update(Affiliation).where(Affiliation.id == affiliation.id).values(refresh_details=False))
        db.session.commit()


def _update_institution(institution: Institution):
    logging.debug('started')

    try:
        if institution.catalog != CATALOG_SCIVAL:
            logging.error(f'What?! Institution catalog is {institution.catalog}')
            return

        institution_data = get_scival_institution(institution.catalog_identifier)

        if not institution_data:
            logging.warning(f'Institution not found {institution.catalog_identifier}')

        institution_data.update_institution(institution)
        institution.refresh_full_details = False

        db.session.add(institution)
        db.session.commit()

    except Exception as e:
        log_exception(e)

        logging.warn('Rolling back transaction')

        db.session.rollback()
        db.session.execute(update(Institution).where(Institution.id == institution.id).values(refresh_full_details=False))
        db.session.commit()


def refresh_publications():
    logging.debug('started')

    try:
        for p in db.session.execute(select(Publication).where(Publication.refresh_full_details == True)).unique().scalars():
            if not p.scopus_catalog_publication and p.doi:
                if pub_data := get_scopus_publication_data(doi=p.doi):
                    save_publications([pub_data])

            if p.scopus_catalog_publication and not p.institutions:
                institutions = get_scival_publication_institutions(p.scopus_catalog_publication.catalog_identifier)
                p.institutions = set(_institutions(institutions))

            p.set_vancouver()

            if p.best_catalog_publication.journal and p.best_catalog_publication.journal.preprint and p.preprint is None:
                p.preprint = True

            if p.is_nihr_acknowledged and p.auto_nihr_acknowledgement is None and p.nihr_acknowledgement is None:
                p.nihr_acknowledgement = p.auto_nihr_acknowledgement = NihrAcknowledgement.get_acknowledged_status()

            p.refresh_full_details = False

        db.session.commit()

    except Exception as e:
        log_exception(e)
        db.session.rollback()

    logging.info('All publications refreshed')
    logging.debug('ended')


def remove_publication_without_catalog_entry():
    logging.debug('started')

    pubs_without_catalog = db.session.execute(
        select(Publication.id)
        .where(Publication.id.not_in(select(CatalogPublication.publication_id)))
    ).scalars().all()

    db.session.execute(
        delete(FolderDoi)
        .where(FolderDoi.publication.has(Publication.id.in_(pubs_without_catalog)))
    )

    db.session.execute(
        delete(Publication)
        .where(Publication.id.in_(pubs_without_catalog))
    )

    db.session.commit()

    logging.debug('ended')


def refresh_catalog_publications():
    logging.debug('started')

    while True:
        p = CatalogPublication.query.filter(CatalogPublication.refresh_full_details == 1).first()

        if not p:
            logging.info('No more catalog publications to refresh')
            break

        _update_catalog_publication(p)

    logging.debug('ended')


def _update_catalog_publication(catalog_publication: CatalogPublication):
    logging.debug(f'Updating publication {catalog_publication.catalog_identifier}')

    try:
        pub_data = None
        if catalog_publication.catalog == CATALOG_SCOPUS:
            pub_data = get_scopus_publication_data(scopus_id=catalog_publication.catalog_identifier)
        if catalog_publication.catalog == CATALOG_OPEN_ALEX:
            pub_data = get_open_alex_publication_data(catalog_publication.catalog_identifier)

        if pub_data:
            save_publications([pub_data])

        catalog_publication.refresh_full_details = False
        db.session.add(catalog_publication)
        db.session.commit()

    except Exception as e:
        log_exception(e)

        db.session.rollback()
        db.session.execute(update(CatalogPublication).where(CatalogPublication.id == catalog_publication.id).values(refresh_full_details=False))
        db.session.commit()


def refresh_Academics():
    logging.debug('started')

    while True:
        a = Academic.query.filter(or_(Academic.updating == 1, Academic.initialised == 0)).filter(Academic.error == 0).first()

        if not a:
            logging.info('No more academics to update')
            break

        _update_academic(a)

    logging.debug('started')


def _update_academic(academic: Academic):
    logging.debug(f'Updating Academic {academic.full_name}')

    try:
        s: Source

        for s in academic.sources:
            if s.error:
                logging.warn(f'Source in ERROR')
            else:
                _update_source(s)

        _find_new_potential_sources(academic)
        _ensure_all_academic_sources_are_proposed(academic)

        academic.ensure_initialisation()
        academic.updating = False
        academic.initialised = True
        db.session.add(academic)
        db.session.commit()

    except Exception as e:
        log_exception(e)

        db.session.rollback()
        db.session.execute(update(Academic).where(Academic.id == academic.id).values(updating=False, error=True))
        db.session.commit()


def _update_source(s):
    try:
        author_data = None

        if s.catalog == CATALOG_SCOPUS:
            author_data = get_scopus_author_data(s.catalog_identifier)
        if s.catalog == CATALOG_OPEN_ALEX:
            author_data = get_open_alex_author_data(s.catalog_identifier)

        if author_data:
            _source_xref_for_author_data_list([author_data])
            affiliation_xref = _affiliation_xref_for_author_data_list([author_data])

            s.affiliations = affiliation_xref[CatalogReference(author_data)]

            author_data.update_source(s)
        else:
            logging.warn(f'Source {s.display_name} not found so setting it to be in error')
            s.error = True

        if s.academic:
            publications = []

            if s.catalog == CATALOG_SCOPUS:
                publications = get_scopus_publications(s.catalog_identifier)
            if s.catalog == CATALOG_OPEN_ALEX:
                publications = get_openalex_publications(s.catalog_identifier)

            add_catalog_publications(publications)

        s.last_fetched_datetime = datetime.utcnow()

        db.session.add(s)
        db.session.flush()
        db.session.commit()

    except Exception as e:
        log_exception(e)
        logging.warn(f'Setting Source {s.display_name} to be in error')
        s.error = True

        db.session.rollback()

        if s and s.id:
            db.session.execute(update(Source).where(Source.id == s.id).values(error=True))
            db.session.commit()


def _find_new_potential_sources(academic):
    logging.debug(f'Finding new sources for {academic.full_name}')

    if len(academic.last_name.strip()) < 1:
        return

    new_source_datas = filter(
        lambda s: s.is_local,
        [*scopus_similar_authors(academic), *open_alex_similar_authors(academic)],
    )

    affiliation_xref = _affiliation_xref_for_author_data_list(new_source_datas)
    new_sources = _source_xref_for_author_data_list(new_source_datas).values()

    for s in new_sources:
        s.affiliations = affiliation_xref[CatalogReference(s)]

    create_potential_sources(new_sources, academic, not_match=True)


def _ensure_all_academic_sources_are_proposed(academic):
    logging.debug(f'Ensuring existing sources are proposed for {academic.full_name}')

    missing_proposed_sources = list(db.session.execute(
        select(Source)
        .where(~Source.potential_academics.any())
        .where(Source.academic == academic)
    ).scalars())

    logging.debug(f'Missing proposed sources found: {missing_proposed_sources}')

    for source in missing_proposed_sources:
        aps = AcademicPotentialSource(
            academic=academic,
            source=source,
        )

        db.session.add(aps)
    
    db.session.commit()


def add_catalog_publications(publication_datas):
    logging.debug('started')

    existing = set()

    keyfunc = lambda a: a.catalog

    for cat, pubs in groupby(sorted(publication_datas, key=keyfunc), key=keyfunc):
        q = select(CatalogPublication).where(
            CatalogPublication.catalog_identifier.in_(p.catalog_identifier for p in pubs)
        ).where(
            CatalogPublication.catalog == cat
        )

        existing = existing | {CatalogReference(cp) for cp in db.session.execute(q).unique().scalars()}


    new_pubs = [p for p in publication_datas if CatalogReference(p) not in existing]

    save_publications(new_pubs)

    logging.debug('ended')


def save_publications(new_pubs):
    logging.info(len(new_pubs))

    journal_xref = _journal_xref_for_publication_data_list(new_pubs)
    subtype_xref = _subtype_xref_for_publication_data_list(new_pubs)
    pubs_xref = _publication_xref_for_publication_data_list(new_pubs)
    sponsor_xref = _sponsor_xref_for_publication_data_list(new_pubs)
    source_xref = _source_xref_for_publication_data_list(new_pubs)
    keyword_xref = _keyword_xref_for_publication_data_list(new_pubs)

    affiliation_xref = _affiliation_xref_for_author_data_list(chain.from_iterable([p.authors for p in new_pubs]))

    for p in new_pubs:
        cpr = CatalogReference(p)
        logging.info(f'Saving Publication {cpr}')

        pub = pubs_xref[cpr]

        cat_pub = db.session.execute(
            select(CatalogPublication)
            .where(CatalogPublication.catalog == p.catalog)
            .where(CatalogPublication.catalog_identifier == p.catalog_identifier)
        ).scalar()

        if not cat_pub:
            cat_pub = CatalogPublication(
                catalog=p.catalog,
                catalog_identifier=p.catalog_identifier,
                refresh_full_details=True,
            )

        cat_pub.publication_id=pub.id
        cat_pub.doi = p.doi or ''
        cat_pub.title = p.title or ''
        cat_pub.publication_cover_date = p.publication_cover_date
        cat_pub.href = p.href
        cat_pub.abstract = p.abstract_text or ''
        cat_pub.funding_text = p.funding_text or ''
        cat_pub.volume = p.volume or ''
        cat_pub.issue = p.issue or ''
        cat_pub.pages = p.pages or ''
        cat_pub.is_open_access = p.is_open_access
        cat_pub.cited_by_count = p.cited_by_count
        cat_pub.journal_id = journal_xref[cpr]
        cat_pub.subtype_id = subtype_xref[cpr]
        cat_pub.sponsors = set(sponsor_xref[cpr])
        cat_pub.keywords = set(keyword_xref[cpr])
        cat_pub.publication_year = p.publication_year
        cat_pub.publication_month = p.publication_month
        cat_pub.publication_day = p.publication_day
        cat_pub.publication_date_text = p.publication_date_text

        if not p.publication_year:
            cat_pub.publication_period_start = cat_pub.publication_period_end = cat_pub.publication_cover_date
        elif p.publication_day:
            cat_pub.publication_period_start = date(year=int(p.publication_year), month=int(p.publication_month), day=int(p.publication_day))
            cat_pub.publication_period_end = cat_pub.publication_period_start
        elif p.publication_month:
            cat_pub.publication_period_start = date(year=int(p.publication_year), month=int(p.publication_month), day=1)
            cat_pub.publication_period_end = cat_pub.publication_period_start + relativedelta(months=1) - relativedelta(days=1)
        else:
            cat_pub.publication_period_start = date(year=int(p.publication_year), month=1, day=1)
            cat_pub.publication_period_end = (cat_pub.publication_period_start + relativedelta(years=1)) - relativedelta(days=1)

        db.session.add(RawData(
            catalog=cat_pub.catalog,
            catalog_identifier=cat_pub.catalog_identifier,
            action=p.action,
            raw_text=p.raw_text,
        ))

        db.session.add(cat_pub)

        pub.validation_historic = (parse_date(p.publication_cover_date) < current_app.config['HISTORIC_PUBLICATION_CUTOFF'])
        db.session.add(pub)

        db.session.commit()

        # When there are lots of sources (authors) for a publication the
        # saving and deleting of these sources (and their associated affiliations)
        # causes SQLAlchemy to fall over, so I've split it up into different bits

        db.session.execute(
            delete(catalog_publications_sources_affiliations)
            .where(CatalogPublicationsSources.id == catalog_publications_sources_affiliations.c.catalog_publications_sources_id)
            .where(CatalogPublicationsSources.catalog_publication_id == cat_pub.id)
        )

        db.session.execute(
            delete(CatalogPublicationsSources)
            .where(CatalogPublicationsSources.catalog_publication_id == cat_pub.id)
        )

        catalog_publication_sources = []

        for i, s in enumerate(source_xref[cpr]):
            cps = CatalogPublicationsSources(
                source=s,
                catalog_publication=cat_pub,
                ordinal=i,
                affiliations=[],
            )
            cps.affiliations_delayed = affiliation_xref[CatalogReference(s)]
            catalog_publication_sources.append(cps)

        db.session.add_all(catalog_publication_sources)
        db.session.commit()

        for c in catalog_publication_sources:
            c.affiliations=c.affiliations_delayed

        db.session.add_all(catalog_publication_sources)
        db.session.commit()
