import logging
from time import sleep
from flask import current_app
from sqlalchemy import and_, or_, select
from academics.catalogs.open_alex import get_open_alex_author_data, open_alex_similar_authors
from academics.catalogs.utils import _add_keywords_to_publications, _add_sponsors_to_publications, _get_funding_acr, _get_journal, _get_subtype
from academics.model import CATALOG_OPEN_ALEX, CATALOG_SCOPUS, Academic, AcademicPotentialSource, CatalogPublication, NihrAcknowledgement, Publication, PublicationsSources, Source, Subtype, Affiliation
from lbrc_flask.celery import celery

from academics.publication_searching import ValidationSearchForm, publication_search_query
from .scopus import get_scopus_author_data, get_scopus_publications, scopus_similar_authors
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

        sleep(30)

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


def add_publications(publication_datas):
    logging.info('add_publications: started')

    for p in publication_datas:
        pub = _get_or_create_publication(p)
        cat_pub = _get_or_create_catalog_publication(p)

        j = _get_journal(p.journal_name)
        st = _get_subtype(p.subtype_code, p.subtype_description)
        fa = _get_funding_acr(p.funding_acronym)

        db.session.add(pub)
        db.session.flush()

        cat_pub.publication = pub

        db.session.add(cat_pub)

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
        cat_pub.author_list = p.author_list or ''

        if p.publication_cover_date < current_app.config['HISTORIC_PUBLICATION_CUTOFF']:
            pub.validation_historic = True

        cat_pub.journal = j
        cat_pub.subtype = st
        cat_pub.funding_acr = fa

        _add_sponsors_to_publications(
            publication=pub,
            sponsor_names=p.funding_list,
        )

        new_sources  = [
            PublicationsSources(
                source=_get_or_create_source(a),
                publication=pub
            ) 
            for a in p.authors
        ]

        pub.publication_sources = new_sources

        db.session.add_all(new_sources)

        _add_keywords_to_publications(publication=pub, keyword_list=p.keywords)

    logging.info('add_publications: ended')


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


def _get_or_create_catalog_publication(p):
    q = (
        select(CatalogPublication)
        .where(and_(
                CatalogPublication.catalog == p.catalog,
                CatalogPublication.catalog_identifier == p.catalog_identifier,
            )
        )).distinct()
    
    result = db.session.execute(q).scalar()

    if result:
        return result
    else:
        return CatalogPublication(
            catalog=p.catalog,
            catalog_identifier=p.catalog_identifier,
        )


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

    sa = db.session.execute(
        select(Affiliation).where(
            Affiliation.catalog_identifier == author_data.affiliation_identifier
        ).where(
            Affiliation.catalog == author_data.catalog
        )
    ).scalar()

    if not sa:
        sa = Affiliation(catalog_identifier=author_data.affiliation_identifier)
    
        sa.name = author_data.affiliation_name
        sa.address = author_data.affiliation_address
        sa.country = author_data.affiliation_country
        sa.catalog = author_data.catalog
    
    s.affiliation = sa

    return s