from itertools import chain
import logging
from flask import current_app
from sqlalchemy import and_, or_, select
from academics.catalogs.open_alex import get_open_alex_author_data, get_openalex_publications, open_alex_similar_authors
from academics.model import CATALOG_OPEN_ALEX, CATALOG_SCOPUS, Academic, AcademicPotentialSource, CatalogPublication, Journal, Keyword, NihrAcknowledgement, Publication, PublicationsSources, Source, Sponsor, Subtype, Affiliation
from lbrc_flask.celery import celery

from academics.publication_searching import ValidationSearchForm, publication_search_query
from .scopus import get_scopus_author_data, get_scopus_publication_data, get_scopus_publications, scopus_similar_authors
from lbrc_flask.database import db
from datetime import datetime
from lbrc_flask.logging import log_exception


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


def update_single_academic(academic: Academic):
    logging.info('update_academic: started')

    academic.mark_for_update()

    db.session.add(academic)
    db.session.commit()

    _process_academics_who_need_an_update.delay()

    logging.info('update_academic: ended')


def update_academics():
    logging.info('update_academics: started')
    if not updating():
        for academic in Academic.query.all():
            logging.info(f'Setting academic {academic.full_name} to be updated')

            academic.mark_for_update()

            db.session.add(academic)

        db.session.commit()

        _process_academics_who_need_an_update.delay()

    logging.info('update_academics: ended')


@celery.task()
def _process_academics_who_need_an_update():
    logging.info('_process_academics_who_need_an_update: started')

    while True:
        a = Academic.query.filter(Academic.updating == 1 and Academic.error == 0).first()

        if not a:
            logging.info(f'_process_academics_who_need_an_update: No more academics to update')
            break

        _update_academic(a)

        db.session.commit()

    logging.info('_process_academics_who_need_an_update: Start doing the publications')

    while True:
        p = CatalogPublication.query.filter(CatalogPublication.refresh_full_details == 1).first()

        if not p:
            logging.info(f'_process_academics_who_need_an_update: No more publications to refresh')
            break

        _update_publication(p)

        db.session.commit()

    delete_orphan_publications()
    auto_validate()

    logging.info('_process_academics_who_need_an_update: Ended')


def _update_academic(academic: Academic):
    logging.info(f'Updating Academic {academic.full_name}')

    try:
        s: Source

        for s in academic.sources:
            if s.error:
                logging.info(f'Source in ERROR')
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


def _update_publication(catalog_publication: CatalogPublication):
    logging.info(f'Updating publication {catalog_publication.catalog_identifier}')

    try:
        if catalog_publication.catalog == CATALOG_SCOPUS:
            pub_data = get_scopus_publication_data(catalog_publication.catalog_identifier)
        # if catalog_publication.catalog == CATALOG_OPEN_ALEX:
        #     pub_data = get_open_alex_publication_data(catalog_publication.catalog_identifier)

        save_publications(pub_data.catalog, [pub_data])

    except Exception as e:
        log_exception(e)

    finally:
        catalog_publication.refresh_full_details = False

        db.session.add(catalog_publication)


def refresh_source(s):
    try:
        author_data = None

        if s.catalog == CATALOG_SCOPUS:
            author_data = get_scopus_author_data(s.catalog_identifier, get_extended_details=True)
        if s.catalog == CATALOG_OPEN_ALEX:
            author_data = get_open_alex_author_data(s.catalog_identifier)

        if author_data:
            s = _get_or_create_source(author_data=author_data)
        else:
            logging.info(f'Source {s.full_name} not found so setting it to be in error')
            s.error = True

        if s.academic:
            publications = []

            if s.catalog == CATALOG_SCOPUS:
                publications = get_scopus_publications(s.catalog_identifier)
            if s.catalog == CATALOG_OPEN_ALEX:
                publications = get_openalex_publications(s.catalog_identifier)

            add_catalog_publications(s.catalog, publications)

        s.last_fetched_datetime = datetime.utcnow()

        db.session.add(s)
        db.session.flush()
        db.session.commit()

    except Exception as e:
        log_exception(e)
        logging.info(f'Setting Source {s.full_name} to be in error')
        s.error = True
    finally:
        db.session.add(s)
        db.session.commit()


def _find_new_scopus_sources(academic):
    logging.info(f'Finding new sources for {academic.full_name}')

    if len(academic.last_name.strip()) < 1:
        return

    new_sources = [a for a in scopus_similar_authors(academic) if a.is_leicester]
    new_sources.extend([a for a in open_alex_similar_authors(academic) if a.is_leicester])

    for new_source in new_sources:
        logging.info(f'Adding new potential source {new_source.catalog_identifier}')

        if db.session.execute(
            select(db.func.count(AcademicPotentialSource.id))
            .where(AcademicPotentialSource.academic == academic)
            .where(AcademicPotentialSource.source.has(Source.catalog_identifier == new_source.catalog_identifier))
            .where(AcademicPotentialSource.source.has(Source.catalog == new_source.catalog))
        ).scalar() > 0:
            continue

        s = db.session.execute(
            select(Source)
            .where(Source.catalog_identifier == new_source.catalog_identifier)
            .where(Source.catalog == new_source.catalog)
        ).scalar()

        if not s:
            logging.info(f'New potential source {new_source.catalog_identifier} from catalog {new_source.catalog} is not currently known')

            s = _get_or_create_source(new_source)
            db.session.add(s)

        db.session.add(AcademicPotentialSource(
            academic=academic,
            source=s,
        ))
   
    db.session.commit()


def _ensure_all_academic_sources_are_proposed(academic):
    logging.info(f'Ensuring existing sources are proposed for {academic.full_name}')

    missing_proposed_sources = list(db.session.execute(
        select(Source)
        .where(~Source.potential_academics.any())
        .where(Source.academic == academic)
    ).scalars())

    logging.info(f'Missing proposed sources found: {missing_proposed_sources}')

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

    _process_academics_who_need_an_update.delay()


def delete_orphan_publications():
    for p in Publication.query.filter(~Publication.publication_sources.any()):
        db.session.delete(p)
        db.session.commit()


def _get_journal_xref(publication_datas):
    logging.info('_get_journal_xref: started')

    names = {p.journal_name for p in publication_datas}

    q = select(Journal.id, Journal.name).where(Journal.name.in_(names))

    xref = {j['name'].lower(): j['id'] for j in db.session.execute(q).mappings()}

    new_journals = [Journal(name=n) for n in xref.keys() - names]

    db.session.add_all(new_journals)
    db.session.commit()

    xref = xref | {j.name.lower(): j.id for j in new_journals}

    return {p.catalog_identifier.lower(): xref[p.journal_name.lower()] for p in publication_datas}


def _get_subtype_xref(publication_datas):
    logging.info('_get_subtype_xref: started')

    descs = {p.subtype_description for p in publication_datas}

    q = select(Subtype.id, Subtype.description).where(Subtype.description.in_(descs))

    xref = {st['description'].lower(): st['id'] for st in db.session.execute(q).mappings()}

    new_subtypes = [Subtype(code=d, description=d) for d in xref.keys() - descs]

    db.session.add_all(new_subtypes)
    db.session.commit()

    xref = xref | {st.description.lower(): st.id for st in new_subtypes}

    return {p.catalog_identifier.lower(): xref[p.subtype_description.lower()] for p in publication_datas}


def _get_publication_xref(catalog, publication_datas):
    logging.info('_get_publication_xref: started')

    ids = {p.catalog_identifier for p in publication_datas}

    print(ids)

    q = select(CatalogPublication).where(
        CatalogPublication.catalog_identifier.in_(ids)
    ).where(
        CatalogPublication.catalog == catalog
    )

    xref = {cp.catalog_identifier.lower(): cp.publication for cp in db.session.execute(q).scalars()}

    print(xref)

    new_pubs = {id: Publication() for id in xref.keys() - ids}

    print(new_pubs)

    db.session.add_all(new_pubs.values())
    db.session.commit()

    print(new_pubs)

    xref = xref | {p.catalog_identifier.lower(): p for p in new_pubs}

    print(xref)

    return {p.catalog_identifier.lower(): xref[p.catalog_identifier.lower()] for p in publication_datas}


def _get_sponsor_xref(publication_datas):
    logging.info('_get_sponsor_xref: started')

    names = {n for n in chain.from_iterable([p.funding_list for p in publication_datas])}

    q = select(Sponsor.id, Sponsor.name).where(Sponsor.name.in_(names))

    xref = {p['name'].lower(): p['id'] for p in db.session.execute(q).mappings()}

    new_sponsors = [Sponsor(name=n) for n in xref.keys() - names]

    db.session.add_all(new_sponsors)
    db.session.commit()

    xref = xref | {s.name.lower(): s.id for s in new_sponsors}

    return {
        p.catalog_identifier.lower(): [xref[n.lower()] for n in p.funding_list]
        for p in publication_datas
    }


def _get_keyword_xref(publication_datas):
    logging.info('_get_keyword_xref: started')

    keywords = {k.strip() for k in chain.from_iterable([p.keywords for p in publication_datas]) if k}

    q = select(Keyword).where(Keyword.keyword.in_(keywords))

    xref = {k.keyword.lower(): k for k in db.session.execute(q).scalars()}

    new_keywords = [Keyword(keyword=k) for k in xref.keys() - keywords]

    db.session.add_all(new_keywords)
    db.session.commit()

    xref = xref | {k.keyword.lower(): k for k in new_keywords}

    return {
        p.catalog_identifier.lower(): [xref[k.strip().lower()] for k in p.keywords if k]
        for p in publication_datas
    }


def _get_affiliation_xref(catalog, author_datas):
    logging.info('_get_affiliation_xref: started')

    affiliations = {a.affiliation_identifier: a for a in author_datas if a.affiliation_identifier}

    q = select(Affiliation).where(
        Affiliation.catalog_identifier.in_(affiliations.keys())
    ).where(
        Affiliation.catalog == catalog
    )

    xref = {a.catalog_identifier.lower(): a for a in db.session.execute(q).scalars()}

    new_affiliations = [
        Affiliation(
            catalog=catalog,
            catalog_identifier=a.affiliation_identifier,
            name=a.affiliation_name,
            address=a.affiliation_address,
            country=a.affiliation_country,
        )
        for a in affiliations.values() if a.catalog_identifier.lower() not in xref.keys()
    ]

    db.session.add_all(new_affiliations)
    db.session.commit()

    xref = xref | {a.catalog_identifier.lower(): a for a in new_affiliations}

    return {a.catalog_identifier.lower(): xref[a.affiliation_identifier.lower()] for a in author_datas if a.affiliation_identifier}


def _get_source_xref(catalog, publication_datas):
    logging.info('_get_source_xref: started')

    authors = {a.catalog_identifier: a for a in chain.from_iterable([p.authors for p in publication_datas])}

    q = select(Source).where(
        Source.catalog_identifier.in_(authors.keys())
    ).where(
        Source.catalog == catalog
    )

    xref = {s.catalog_identifier.lower(): s for s in db.session.execute(q).scalars()}

    new_sources = [a.get_new_source() for a in authors.values() if a.catalog_identifier not in xref.keys()]

    affiliation_xref = _get_affiliation_xref(catalog, authors.values())

    for a in new_sources:
        a.affiliation = affiliation_xref[a.catalog_identifier]

    db.session.add_all(new_sources)
    db.session.commit()

    xref = xref | {s.catalog_identifier.lower(): s for s in new_sources}

    return {
        p.catalog_identifier.lower(): [xref[a.catalog_identifier.lower()] for a in p.authors]
        for p in publication_datas
    }


def add_catalog_publications(catalog, publication_datas):
    logging.info('add_catalog_publications: started')

    q = (
        select(CatalogPublication.catalog_identifier)
        .where(CatalogPublication.catalog == catalog)
        .where(CatalogPublication.catalog_identifier.in_(
            p.catalog_identifier for p in publication_datas
        ))
    )

    existing_cat_ids = {db.session.execute(q).scalars()}
    new_pubs = [p for p in publication_datas if p.catalog_identifier not in existing_cat_ids]

    save_publications(catalog, new_pubs)

    logging.info('add_publications: ended')


def save_publications(catalog, new_pubs):
    journal_xref = _get_journal_xref(new_pubs)
    subtype_xref = _get_subtype_xref(new_pubs)
    pubs_xref = _get_publication_xref(catalog, new_pubs)
    sponsor_xref = _get_sponsor_xref(new_pubs)
    source_xref = _get_source_xref(catalog, new_pubs)
    keyword_xref = _get_keyword_xref(new_pubs)

    for p in new_pubs:
        logging.info(f'Adding Publication {p.catalog}: {p.catalog_identifier}')

        pub = pubs_xref[p.catalog_identifier]

        cat_pub = db.session.execute(
            select(CatalogPublication.catalog_identifier)
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

        cat_pub = CatalogPublication(
            doi=p.doi or '',
            title=p.title or '',
            publication_cover_date=p.publication_cover_date,
            href=p.href,
            abstract=p.abstract_text or '',
            funding_text=p.funding_text or '',
            volume=p.volume or '',
            issue=p.issue or '',
            pages=p.pages or '',
            is_open_access=p.is_open_access,
            cited_by_count=p.cited_by_count,
            author_list=p.author_list or '',
            journal_id=journal_xref[p.catalog_identifier],
            subtype_id=subtype_xref[p.catalog_identifier],
        )

        cat_pub.sponsors = sponsor_xref[p.catalog_identifier]
        cat_pub.keywords = keyword_xref[p.catalog_identifier]

        print('v'*40)
        print(source_xref)
        print('-'*40)
        print(pub)
        print('-'*40)
        print(source_xref[p.catalog_identifier])
        print('^'*40)

        publication_sources = [
            PublicationsSources(
                source=s,
                publication=pub
            ) 
            for s in source_xref[p.catalog_identifier]
        ]

        pub.publication_sources = publication_sources
        pub.validation_historic = (p.publication_cover_date < current_app.config['HISTORIC_PUBLICATION_CUTOFF'])

        db.session.add_all(publication_sources)
        db.session.add(cat_pub)
        db.session.add(pub)


def _get_or_create_source(author_data):
    s = None

    s = db.session.execute(
        select(Source)
        .where(Source.catalog == author_data.catalog)
        .where(Source.catalog_identifier == author_data.catalog_identifier)
    ).scalar()

    if not s:
        s = author_data.get_new_source()
    else:
        author_data.update_source(s)
    
    db.session.add(s)

    a = db.session.execute(
        select(Affiliation)
        .where(Affiliation.catalog_identifier == author_data.affiliation_identifier)
        .where(Affiliation.catalog == author_data.catalog)
    ).scalar()

    if not a:
        a = Affiliation(catalog_identifier=author_data.affiliation_identifier)
    
        a.name = author_data.affiliation_name
        a.address = author_data.affiliation_address
        a.country = author_data.affiliation_country
        a.catalog = author_data.catalog
    
    s.affiliation = a

    return s
