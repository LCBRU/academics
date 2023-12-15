import logging
from sqlalchemy import and_, or_, select
from academics.catalogs.open_alex import get_open_alex_author_data, get_openalex_publications, open_alex_similar_authors
from academics.catalogs.utils import _get_journal, _get_subtype
from academics.model import CATALOG_OPEN_ALEX, CATALOG_SCOPUS, Academic, AcademicPotentialSource, CatalogPublication, Journal, NihrAcknowledgement, Publication, Source, Subtype, Affiliation
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

        _update_publication(p)

        if not p:
            logging.info(f'_process_academics_who_need_an_update: No more publications to refresh')
            break

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

            add_publications(publications)

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

    names = {n for n in {p.journal_name for p in publication_datas}}

    logging.info('_get_journal_xref: getting existing')

    existing_q = select(
        Journal.id,
        Journal.name,
    ).where(
        Journal.name.in_(names)
    )

    logging.info('_get_journal_xref: rejigging')

    xref = {
        j['name']: j['id'] for j in db.session.execute(existing_q).mappings()
    }

    logging.info('_get_journal_xref: whats missing')

    missing = xref.keys() - names

    logging.info('_get_journal_xref: creating new ones')

    new_journals = [Journal(name=m) for m in missing]

    logging.info('_get_journal_xref: Adding to DB')

    db.session.add_all(new_journals)
    db.session.commit()

    logging.info('_get_journal_xref: Merging')

    xref.extend({j.name: j.id for j in new_journals})

    logging.info('_get_journal_xref: Second rejigging')

    return {p.catalog_identifier: xref[p.journal_name] for p in publication_datas}


def _get_subtype_xref(publication_datas):
    return {d: _get_subtype(c, d) for c, d in {(p.subtype_code, p.subtype_description) for p in publication_datas}}


def _get_publication_xref(publication_datas):
    return {(p.catalog, p.catalog_identifier): _get_or_create_publication(p) for p in publication_datas}


def add_publications(publication_datas):
    logging.info('add_publications: started')

    journal_xref = _get_journal_xref(publication_datas)

    print(journal_xref)

    # subtype_xref = _get_subtype_xref(publication_datas)
    # publication_xref = _get_publication_xref(publication_datas)

    print('Hello')

    # db.session.add_all(journals.values())
    # db.session.add_all(subtypes.values())
    # db.session.add_all(publications.values())

    # db.session.commit()

    # for p in publication_datas:
    #     pub = publications[(p.catalog, p.catalog_identifier)]

    #     logging.info(f'publication: {p.catalog_identifier} - getting cat pub')

    #     cat_pub = _get_catalog_publication(p)

    #     logging.info(f'publication: {p.catalog_identifier} - got cat pub')

    #     if cat_pub:
    #         logging.info(f'publication: {p.catalog_identifier} - skipping')
    #         continue

    #     cat_pub = CatalogPublication(
    #         catalog=p.catalog,
    #         catalog_identifier=p.catalog_identifier,
    #     )

    #     logging.info(f'publication: {p.catalog_identifier} - flushed')

    #     cat_pub.publication = pub

    #     logging.info(f'publication: {p.catalog_identifier} - adding cat to pub')

    #     db.session.add(cat_pub)

    #     logging.info(f'publication: {p.catalog_identifier} - setting values')

    #     cat_pub.doi = p.doi or ''
    #     cat_pub.title = p.title or ''
    #     cat_pub.publication_cover_date = p.publication_cover_date
    #     cat_pub.href = p.href
    #     cat_pub.abstract = p.abstract_text or ''
    #     cat_pub.funding_text = p.funding_text or ''
    #     cat_pub.volume = p.volume or ''
    #     cat_pub.issue = p.issue or ''
    #     cat_pub.pages = p.pages or ''
    #     cat_pub.refresh_full_details = True

    #     cat_pub.is_open_access = p.is_open_access
    #     cat_pub.cited_by_count = p.cited_by_count
    #     cat_pub.author_list = p.author_list or ''

    #     if p.publication_cover_date < current_app.config['HISTORIC_PUBLICATION_CUTOFF']:
    #         pub.validation_historic = True

    #     logging.info(f'publication: {p.catalog_identifier} - set values')

    #     cat_pub.journal = journals[p.journal_name]
    #     cat_pub.subtype = subtypes[p.subtype_description]

    #     logging.info(f'publication: {p.catalog_identifier} - set subtype - adding sponsors')

    #     _add_sponsors_to_publications(
    #         publication=pub,
    #         sponsor_names=p.funding_list,
    #     )

    #     logging.info(f'publication: {p.catalog_identifier} - sponsors adding - creating sources')

    #     pub_sources  = [
    #         PublicationsSources(
    #             source=s,
    #             publication=pub
    #         ) 
    #         for s in [_get_or_create_source(a) for a in p.authors]
    #     ]

    #     logging.info(f'publication: {p.catalog_identifier} - adding sources')

    #     pub.publication_sources = pub_sources

    #     logging.info(f'publication: {p.catalog_identifier} - saving sources')

    #     db.session.add_all(pub_sources)

    #     logging.info(f'publication: {p.catalog_identifier} - saving pub')

    #     db.session.add(pub)

    #     logging.info(f'publication: {p.catalog_identifier} - adding keywords')

    #     _add_keywords_to_publications(publication=pub, keyword_list=p.keywords)

    #     logging.info(f'publication: {p.catalog_identifier} is done')


    # logging.info('add_publications: ended')



def _get_or_create_publication(p):
    q = (
        select(Publication)
        .join(Publication.catalog_publications)
        .where(or_(
            CatalogPublication.doi == p.doi,
            and_(
                CatalogPublication.catalog == p.catalog,
                CatalogPublication.catalog_identifier == p.catalog_identifier,
            )
        ))).distinct()
    
    result = db.session.execute(q).scalar()

    if result:
        return result
    else:
        return Publication()


def _get_catalog_publication(p):
    q = (
        select(CatalogPublication)
        .where(and_(
                CatalogPublication.catalog == p.catalog,
                CatalogPublication.catalog_identifier == p.catalog_identifier,
            )
        )).distinct()
    
    return db.session.execute(q).scalar()


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
