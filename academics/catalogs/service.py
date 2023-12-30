from itertools import chain, groupby
import logging
from flask import current_app
from sqlalchemy import select
from academics.catalogs.open_alex import get_open_alex_author_data, get_open_alex_publication_data, get_openalex_publications, open_alex_similar_authors
from academics.catalogs.utils import CatalogReference
from academics.model import CATALOG_OPEN_ALEX, CATALOG_SCOPUS, Academic, AcademicPotentialSource, CatalogPublication, CatalogPublicationsSources, Journal, Keyword, NihrAcknowledgement, Publication, Source, Sponsor, Subtype, Affiliation
from lbrc_flask.celery import celery
from academics.publication_searching import ValidationSearchForm, publication_search_query
from .scopus import get_scopus_author_data, get_scopus_publication_data, get_scopus_publications, scopus_similar_authors
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

    while True:
        a = Academic.query.filter(Academic.updating == 1 and Academic.error == 0).first()

        if not a:
            logging.info(f'_process_updates: No more academics to update')
            break

        _update_academic(a)

        db.session.commit()

    logging.debug('_process_updates: Start doing the publications')

    while True:
        p = CatalogPublication.query.filter(CatalogPublication.refresh_full_details == 1).first()

        if not p:
            logging.info(f'_process_updates: No more catalog publications to refresh')
            break

        _update_catalog_publication(p)

        db.session.commit()

    while True:
        p = Publication.query.filter(Publication.vancouver == None).first()

        if not p:
            logging.info(f'_process_updates: No more publications to refresh')
            break

        _update_publication(p)

        db.session.commit()

    while True:
        a = Affiliation.query.filter(Affiliation.refresh_details == 1).first()

        if not a:
            logging.info(f'_process_updates: No more affiliations to refresh')
            break

        _update_affiliation(a)

        db.session.commit()

    auto_validate()

    logging.debug('_process_updates: Ended')


def _update_affiliation(affiliation: Affiliation):
    logging.debug(f'Updating Affiliation {affiliation.line_summary}')

    try:
        if affiliation.catalog == CATALOG_SCOPUS:
            pub_data = get_scopus_publication_data(affiliation.catalog_identifier)
        if affiliation.catalog == CATALOG_OPEN_ALEX:
            pub_data = get_open_alex_publication_data(affiliation.catalog_identifier)

        affiliation.refresh_details = False

    finally:
        db.session.add(affiliation)


def _update_academic(academic: Academic):
    logging.debug(f'Updating Academic {academic.full_name}')

    try:
        s: Source

        for s in academic.sources:
            if s.error:
                logging.warn(f'Source in ERROR')
            else:
                refresh_source(s)

        _find_new_scopus_sources(academic)

        _ensure_all_academic_sources_are_proposed(academic)

        academic.ensure_initialisation()
        academic.updating = False

    except Exception as e:
        log_exception(e)
        academic.error = True

    finally:
        db.session.add(academic)


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


def _update_publication(publication: Publication):
    logging.debug(f'Updating publication {publication.id}')

    publication.set_vancouver()

    db.session.add(publication)


def refresh_source(s):
    try:
        author_data = None

        if s.catalog == CATALOG_SCOPUS:
            author_data = get_scopus_author_data(s.catalog_identifier, get_extended_details=True)
        if s.catalog == CATALOG_OPEN_ALEX:
            author_data = get_open_alex_author_data(s.catalog_identifier)

        if author_data:
            a = _get_source_xref([author_data])[CatalogReference(s)]
            affiliation_xref = _get_affiliation_xref([author_data])

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


def _find_new_scopus_sources(academic):
    logging.debug(f'Finding new sources for {academic.full_name}')

    if len(academic.last_name.strip()) < 1:
        return

    existing_sources = {CatalogReference(s.source) for s in db.session.execute(
        select(AcademicPotentialSource)
        .where(AcademicPotentialSource.academic == academic)
    ).scalars()}

    new_source_datas = filter(
        lambda s: s.is_leicester,
        [*scopus_similar_authors(academic), *open_alex_similar_authors(academic)],
    )

    affiliation_xref = _get_affiliation_xref(new_source_datas)
    new_sources = _get_source_xref(new_source_datas).values()

    for s in new_sources:
        s.affiliations = affiliation_xref[CatalogReference(s)]

    potentials = [
        AcademicPotentialSource(academic=academic, source=s)
        for s in new_sources
        if CatalogReference(s) not in existing_sources
    ]

    db.session.add_all(potentials)
    db.session.commit()


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


def add_sources_to_academic(catalog_identifier, academic_id=None, theme_id=None):
    academic = None

    if academic_id:
        academic = db.session.get(Academic, academic_id)

    if not academic:
        academic = Academic(
            theme_id=theme_id,
        )
    
    academic.updating = True

    db.session.add(academic)

    for catalog_identifier in catalog_identifier:
        sa = Source(
            catalog_identifier=catalog_identifier,
            catalog=CATALOG_SCOPUS,
            academic=academic,
        )
        db.session.add(sa)

    db.session.commit()

    _process_updates.delay()


def _get_journal_xref(publication_datas):
    logging.debug('_get_journal_xref: started')

    names = {p.journal_name for p in publication_datas}

    q = select(Journal.id, Journal.name).where(Journal.name.in_(names))

    xref = {j['name'].lower(): j['id'] for j in db.session.execute(q).mappings()}

    new_journals = [Journal(name=n) for n in names - xref.keys()]

    db.session.add_all(new_journals)
    db.session.commit()

    xref = xref | {j.name.lower(): j.id for j in new_journals}

    return {CatalogReference(p): xref[p.journal_name.lower()] for p in publication_datas}


def _get_subtype_xref(publication_datas):
    logging.debug('_get_subtype_xref: started')

    descs = {p.subtype_description for p in publication_datas}

    q = select(Subtype.id, Subtype.description).where(Subtype.description.in_(descs))

    xref = {st['description'].lower(): st['id'] for st in db.session.execute(q).mappings()}

    new_subtypes = [Subtype(code=d, description=d) for d in descs - xref.keys()]

    db.session.add_all(new_subtypes)
    db.session.commit()

    xref = xref | {st.description.lower(): st.id for st in new_subtypes}

    return {CatalogReference(p): xref[p.subtype_description.lower()] for p in publication_datas}


def _get_publication_xref(publication_datas):
    logging.debug('_get_publication_xref: started')

    xref = {}

    keyfunc = lambda a: a.catalog

    for cat, pubs in groupby(sorted(publication_datas, key=keyfunc), key=keyfunc):
        q = select(CatalogPublication).where(
            CatalogPublication.catalog_identifier.in_([p.catalog_identifier for p in pubs])
        ).where(
            CatalogPublication.catalog == cat
        )

        xref = xref | {CatalogReference(cp): cp.publication for cp in db.session.execute(q).scalars()}

    new_pubs = {CatalogReference(p): Publication() for p in publication_datas if CatalogReference(p) not in xref.keys()}

    db.session.add_all(new_pubs.values())
    db.session.commit()

    xref = xref | new_pubs

    return {CatalogReference(p): xref[CatalogReference(p)] for p in publication_datas}


def _get_sponsor_xref(publication_datas):
    logging.debug('_get_sponsor_xref: started')

    names = set(filter(None, [n for n in chain.from_iterable([p.funding_list for p in publication_datas])]))

    q = select(Sponsor.id, Sponsor.name).where(Sponsor.name.in_(names))

    xref = {p['name'].lower(): p['id'] for p in db.session.execute(q).mappings()}

    new_sponsors = [Sponsor(name=n) for n in names - xref.keys()]

    db.session.add_all(new_sponsors)
    db.session.commit()

    xref = xref | {s.name.lower(): s.id for s in new_sponsors}

    return {
        CatalogReference(p): [xref[n.lower()] for n in p.funding_list if n]
        for p in publication_datas
    }


def _get_keyword_xref(publication_datas):
    logging.debug('_get_keyword_xref: started')

    keywords = {k.strip() for k in chain.from_iterable([p.keywords for p in publication_datas]) if k}

    q = select(Keyword).where(Keyword.keyword.in_(keywords))

    xref = {k.keyword.lower(): k for k in db.session.execute(q).scalars()}

    new_keywords = [Keyword(keyword=k) for k in keywords - xref.keys()]

    db.session.add_all(new_keywords)
    db.session.commit()

    xref = xref | {k.keyword.lower(): k for k in new_keywords}

    return {
        CatalogReference(p): [xref[k.strip().lower()] for k in p.keywords if k]
        for p in publication_datas
    }


def _get_affiliation_xref(author_datas):
    logging.debug('_get_affiliation_xref: started')

    author_datas = list(author_datas)

    affiliations = {CatalogReference(af): af for af in chain.from_iterable([a.affiliations for a in author_datas])}

    xref = {}

    keyfunc = lambda a: a.catalog

    for cat, afils in groupby(sorted(affiliations.values(), key=keyfunc), key=keyfunc):

        afils = list(afils)

        q = select(Affiliation).where(
            Affiliation.catalog_identifier.in_([a.catalog_identifier for a in afils])
        ).where(
            Affiliation.catalog == cat
        )

        xref = xref | {CatalogReference(a): a for a in db.session.execute(q).scalars()}

        new_affiliations = [
            Affiliation(
                catalog=cat,
                catalog_identifier=a.catalog_identifier,
                name=a.name,
                address=a.address,
                country=a.country,
                refresh_details=True,
            )
            for a in afils if CatalogReference(a) not in xref.keys()
        ]

        db.session.add_all(new_affiliations)
        db.session.commit()

        xref = xref | {CatalogReference(a): a for a in new_affiliations}

    return {
        CatalogReference(a): [xref[CatalogReference(af)] for af in a.affiliations]
        for a in author_datas
    }


def _get_source_xref_from_publications(publication_datas):
    logging.debug('_get_source_publication_xref: started')

    authors = {CatalogReference(a): a for a in chain.from_iterable([p.authors for p in publication_datas])}

    author_xref = _get_source_xref(authors.values())

    return {
        CatalogReference(p): [author_xref[CatalogReference(a)] for a in p.authors]
        for p in publication_datas
    }


def _get_source_xref(author_datas):
    logging.debug('_get_author_xref: started')

    xref = {}

    keyfunc = lambda a: a.catalog

    for cat, authors in groupby(sorted(author_datas, key=keyfunc), key=keyfunc):
        q = select(Source).where(
            Source.catalog_identifier.in_([a.catalog_identifier for a in authors])
        ).where(
            Source.catalog == cat
        )

        xref = xref | {CatalogReference(a): a for a in db.session.execute(q).scalars()}

    new_sources = [a.get_new_source() for a in author_datas if CatalogReference(a) not in xref.keys()]

    db.session.add_all(new_sources)
    db.session.commit()

    return xref | {CatalogReference(s): s for s in new_sources}


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

        existing = existing | {CatalogReference(cp) for cp in db.session.execute(q).scalars()}


    new_pubs = [p for p in publication_datas if CatalogReference(p) not in existing]

    save_publications(new_pubs)

    logging.debug('add_publications: ended')


def save_publications(new_pubs):
    journal_xref = _get_journal_xref(new_pubs)
    subtype_xref = _get_subtype_xref(new_pubs)
    pubs_xref = _get_publication_xref(new_pubs)
    sponsor_xref = _get_sponsor_xref(new_pubs)
    source_xref = _get_source_xref_from_publications(new_pubs)
    keyword_xref = _get_keyword_xref(new_pubs)

    affiliation_xref = _get_affiliation_xref(chain.from_iterable([p.authors for p in new_pubs]))

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
        cat_pub.sponsors = sponsor_xref[cpr]
        cat_pub.keywords = keyword_xref[cpr]

        catalog_publication_sources = [
            CatalogPublicationsSources(
                source=s,
                catalog_publication=cat_pub,
                ordinal=i,
                affiliations=affiliation_xref[CatalogReference(s)]
            ) 
            for i, s in enumerate(source_xref[cpr])
        ]

        cat_pub.catalog_publication_sources = catalog_publication_sources
        pub.validation_historic = (parse_date(p.publication_cover_date) < current_app.config['HISTORIC_PUBLICATION_CUTOFF'])

        db.session.add(cat_pub)
        db.session.add(pub)
        db.session.commit()
