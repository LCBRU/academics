from itertools import chain, groupby
import logging
from flask import current_app
from sqlalchemy import delete, select
from academics.catalogs.open_alex import get_open_alex_affiliation_data, get_open_alex_author_data, get_open_alex_publication_data, get_openalex_publications, open_alex_similar_authors
from academics.catalogs.data_classes import CatalogReference, _affiliation_xref_for_author_data_list, _journal_xref_for_publication_data_list, _keyword_xref_for_publication_data_list, _publication_xref_for_publication_data_list, _source_xref_for_author_data_list, _source_xref_for_publication_data_list, _sponsor_xref_for_publication_data_list, _subtype_xref_for_publication_data_list
from academics.model import CATALOG_OPEN_ALEX, CATALOG_SCOPUS, Academic, AcademicPotentialSource, CatalogPublication, CatalogPublicationsSources, NihrAcknowledgement, Publication, Source, Subtype, Affiliation, catalog_publications_sources_affiliations
from lbrc_flask.celery import celery
from academics.publication_searching import ValidationSearchForm, publication_search_query
from .scopus import get_scopus_affiliation_data, get_scopus_author_data, get_scopus_publication_data, get_scopus_publications, scopus_similar_authors
from lbrc_flask.database import db
from datetime import datetime
from lbrc_flask.logging import log_exception
from lbrc_flask.validators import parse_date


def updating():
    result = Academic.query.filter(Academic.updating == True).count() > 0
    logging.info(f'updating: {result}')
    return result


def auto_validate():
    form = ValidationSearchForm(meta={'csrf': False})
    form.subtype_id.data = [s.id for s in Subtype.get_validation_types()]
    form.supress_validation_historic.data = False
    form.nihr_acknowledgement_id.data = -1

    q = publication_search_query(form)

    amended_count = 0

    for p in db.session.execute(q).all():
        auto_ack = _get_nihr_acknowledgement(p)

        if auto_ack:
            amended_count += 1

            p.auto_nihr_acknowledgement = auto_ack
            p.nihr_acknowledgement = auto_ack

            db.session.add(p)

    db.session.commit()

    return amended_count


def _get_nihr_acknowledgement(pub):
    if pub.is_nihr_acknowledged:
        return NihrAcknowledgement.get_instance_by_name(NihrAcknowledgement.NIHR_ACKNOWLEDGED)


def refresh():
    logging.debug('refresh: started')

    _process_updates.delay()

    logging.debug('refresh: ended')


def add_sources_to_academic(catalog, catalog_identifiers, academic_id=None, theme_id=None):
    academic = None

    if academic_id:
        academic = db.session.get(Academic, academic_id)

    if not academic:
        academic = Academic(
            theme_id=theme_id,
        )
    
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
    logging.debug('update_academic: started')

    academic.mark_for_update()

    db.session.add(academic)
    db.session.commit()

    _process_updates.delay()

    logging.debug('update_academic: ended')


def update_academics():
    logging.debug('update_academics: started')
    if not updating():
        for academic in Academic.query.all():
            logging.debug(f'Setting academic {academic.full_name} to be updated')

            academic.mark_for_update()

            db.session.add(academic)

        db.session.commit()

        _process_updates.delay()

    logging.debug('update_academics: ended')


@celery.task()
def _process_updates():
    logging.debug('_process_updates: started')

    refresh_Academics()
    refresh_catalog_publications()
    refresh_publications()
    refresh_affiliations()
    auto_validate()

    logging.debug('_process_updates: Ended')


def refresh_affiliations():
    logging.debug('refresh_affiliations: started')

    while True:
        a = Affiliation.query.filter(Affiliation.refresh_details == 1).first()

        if not a:
            logging.info(f'refresh_affiliations: No more affiliations to refresh')
            break

        _update_affiliation(a)

        db.session.commit()

    logging.debug('refresh_affiliations: ended')


def _update_affiliation(affiliation: Affiliation):
    logging.debug(f'Updating Affiliation {affiliation.line_summary}')

    try:
        if affiliation.catalog == CATALOG_SCOPUS:
            aff_data = get_scopus_affiliation_data(affiliation.catalog_identifier)
        if affiliation.catalog == CATALOG_OPEN_ALEX:
            aff_data = get_open_alex_affiliation_data(affiliation.catalog_identifier)

        aff_data.update_affiliation(affiliation)

        affiliation.refresh_details = False

    finally:
        db.session.add(affiliation)


def refresh_publications():
    logging.debug('refresh_publications: started')

    while True:
        p = Publication.query.filter(Publication.vancouver == None).first()

        if not p:
            logging.info(f'refresh_publications: No more publications to refresh')
            break

        _update_publication(p)

        db.session.commit()

    logging.debug('refresh_publications: ended')


def _update_publication(publication: Publication):
    logging.debug(f'Updating publication {publication.id}')

    publication.set_vancouver()

    db.session.add(publication)


def refresh_catalog_publications():
    logging.debug('refresh_catalog_publications: started')

    while True:
        p = CatalogPublication.query.filter(CatalogPublication.refresh_full_details == 1).first()

        if not p:
            logging.info(f'refresh_catalog_publications: No more catalog publications to refresh')
            break

        _update_catalog_publication(p)

        db.session.commit()

    logging.debug('refresh_catalog_publications: ended')


def _update_catalog_publication(catalog_publication: CatalogPublication):
    logging.debug(f'Updating publication {catalog_publication.catalog_identifier}')

    try:
        if catalog_publication.catalog == CATALOG_SCOPUS:
            pub_data = get_scopus_publication_data(catalog_publication.catalog_identifier)
        if catalog_publication.catalog == CATALOG_OPEN_ALEX:
            pub_data = get_open_alex_publication_data(catalog_publication.catalog_identifier)

        if pub_data:
            save_publications([pub_data])

    except Exception as e:
        log_exception(e)

    finally:
        catalog_publication.refresh_full_details = False

        db.session.add(catalog_publication)


def refresh_Academics():
    logging.debug('refresh_Academics: started')

    while True:
        a = Academic.query.filter(Academic.updating == 1 and Academic.error == 0).first()

        if not a:
            logging.info(f'refresh_Academics: No more academics to update')
            break

        _update_academic(a)

        db.session.commit()

    logging.debug('refresh_Academics: started')


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

    except Exception as e:
        log_exception(e)
        academic.error = True

    finally:
        db.session.add(academic)


def _update_source(s):
    try:
        author_data = None

        if s.catalog == CATALOG_SCOPUS:
            author_data = get_scopus_author_data(s.catalog_identifier, get_extended_details=True)
        if s.catalog == CATALOG_OPEN_ALEX:
            author_data = get_open_alex_author_data(s.catalog_identifier)

        if author_data:
            a = _source_xref_for_author_data_list([author_data])[CatalogReference(s)]
            affiliation_xref = _affiliation_xref_for_author_data_list([author_data])

            s.affiliations = affiliation_xref[CatalogReference(s)]
        else:
            logging.warn(f'Source {s.full_name} not found so setting it to be in error')
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
        logging.warn(f'Setting Source {s.full_name} to be in error')
        s.error = True
    finally:
        db.session.add(s)
        db.session.commit()


def _find_new_potential_sources(academic):
    logging.debug(f'Finding new sources for {academic.full_name}')

    if len(academic.last_name.strip()) < 1:
        return

    new_source_datas = filter(
        lambda s: s.is_leicester,
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
    logging.debug('add_catalog_publications: started')

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

    logging.debug('add_publications: ended')


def save_publications(new_pubs):
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
                publication_id=pub.id,
                refresh_full_details=True,
            )

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

        db.session.add(cat_pub)

        pub.validation_historic = (parse_date(p.publication_cover_date) < current_app.config['HISTORIC_PUBLICATION_CUTOFF'])
        db.session.add(pub)

        db.session.commit()

        # When there are lots of sources (authors) for a publication the
        # saving and deleting of these sources (and their associated affiliations)
        # causes SQLAlchemy to fall over, so I've split it up into different bits

        db.session.execute(
            delete(catalog_publications_sources_affiliations)
            .where(catalog_publications_sources_affiliations.c.catalog_publications_sources_id.in_(
                select(CatalogPublicationsSources.id)
                .where(CatalogPublicationsSources.catalog_publication_id == cat_pub.id)
            ))
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
