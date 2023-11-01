import logging
from time import sleep
from flask import current_app
from sqlalchemy import and_, or_, select
from academics.catalogs.open_alex import open_alex_similar_authors
from academics.catalogs.utils import _add_keywords_to_publications, _add_sponsors_to_publications, _get_funding_acr, _get_journal, _get_sponsor, _get_subtype
from academics.model import Academic, AcademicPotentialSource, NihrAcknowledgement, NihrFundedOpenAccess, ScopusAuthor, ScopusPublication, Source, Subtype
from lbrc_flask.celery import celery
from .scopus import get_scopus_author_data, get_scopus_publications, scopus_similar_authors
from lbrc_flask.database import db
from datetime import datetime
from lbrc_flask.logging import log_exception


def updating():
    result = Academic.query.filter(Academic.updating == True).count() > 0
    logging.info(f'updating: {result}')
    return result


def auto_validate():
    q = ScopusPublication.query
    q = q.filter(and_(
            ScopusPublication.nihr_acknowledgement_id == None,
            ScopusPublication.nihr_funded_open_access_id == None,
        ))
    q = q.filter(or_(
            ScopusPublication.validation_historic == False,
            ScopusPublication.validation_historic == None,
        ))
    q = q.filter(ScopusPublication.subtype_id.in_([s.id for s in Subtype.get_validation_types()]))

    amended_count = 0

    for p in q.all():
        auto_ack = _get_nihr_acknowledgement(p)
        auto_open = _get_nihr_funded_open_access(p)

        if auto_ack or auto_open:
            amended_count += 1

            p.auto_nihr_acknowledgement = auto_ack
            p.nihr_acknowledgement = auto_ack

            p.auto_nihr_funded_open_access = auto_open
            p.nihr_funded_open_access = auto_open

            db.session.add(p)

    db.session.commit()

    return amended_count


def _get_nihr_acknowledgement(pub):
    if pub.is_nihr_acknowledged:
        return NihrAcknowledgement.get_instance_by_name(NihrAcknowledgement.NIHR_ACKNOWLEDGED)


def _get_nihr_funded_open_access(pub):
    if pub.all_nihr_acknowledged and pub.is_open_access:
        return NihrFundedOpenAccess.get_instance_by_name(NihrFundedOpenAccess.NIHR_FUNDED)


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
                update_source(s)

        _find_new_scopus_sources(academic)

        _ensure_all_academic_sources_are_proposed(academic)

        academic.ensure_initialisation()
        academic.updating = False

    except Exception as e:
        log_exception(e)
        academic.error = True

    finally:
        db.session.add(academic)


def update_source(s):
    try:
        author_data = None

        if isinstance(s, ScopusAuthor) and current_app.config['SCOPUS_ENABLED']:
            author_data = get_scopus_author_data(s.source_identifier)

        if author_data:
            sleep(1)
            author_data.update_source(s, True)

        if s.academic:
            publications = []

            if isinstance(s, ScopusAuthor) and current_app.config['SCOPUS_ENABLED']:
                publications = get_scopus_publications(s.source_identifier)
            
            add_publications(publications, s)

        s.last_fetched_datetime = datetime.utcnow()
    except Exception as e:
        log_exception(e)
        logging.info(f'Setting Source {s.full_name} to be in error')
        s.error = True
    finally:
        db.session.add(s)


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
            .where(AcademicPotentialSource.source.has(Source.source_identifier == new_source.catalog_identifier))
            .where(AcademicPotentialSource.source.has(Source.type == new_source.catalog))
        ).scalar() > 0:
            continue

        s = db.session.execute(
            select(Source)
            .where(Source.source_identifier == new_source.catalog_identifier)
            .where(Source.type == new_source.catalog)
        ).scalar()

        if not s:
            logging.info(f'New potential source {new_source.catalog_identifier} from catalog {new_source.catalog} is not currently known')

            sleep(1)
            s = new_source.get_new_source()
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


def add_sources_to_academic(source_identifiers, academic_id=None, theme_id=None):
    academic = None

    if academic_id:
        academic = db.session.get(Academic, academic_id)

    if not academic:
        academic = Academic(
            theme_id=theme_id,
        )
    
    academic.updating = True

    db.session.add(academic)

    for source_identifier in source_identifiers:
        sa = ScopusAuthor(
            source_identifier=source_identifier,
            academic=academic,
        )
        db.session.add(sa)

    db.session.commit()

    _process_academics_who_need_an_update.delay()


def delete_orphan_publications():
    for p in ScopusPublication.query.filter(~ScopusPublication.sources.any()):
        db.session.delete(p)
        db.session.commit()


def add_publications(publication_datas, source):
    logging.info('add_publications: started')

    for p in publication_datas:
        publication = ScopusPublication.query.filter(ScopusPublication.scopus_id == p.catalog_identifier).one_or_none()

        if not publication:
            publication = ScopusPublication(scopus_id=p.catalog_identifier)
            publication.funding_text = p.abstract.funding_text
            _add_sponsors_to_publications(
                publication=publication,
                sponsor_names=p.abstract.funding_list,
            )

        db.session.add(publication)

        publication.doi = p.doi
        publication.title = p.title
        publication.journal = _get_journal(p.journal_name)
        publication.publication_cover_date = p.publication_cover_date
        publication.href = p.href
        publication.abstract = p.abstract_text
        publication.volume = p.volume
        publication.issue = p.issue
        publication.pages = p.pages
        publication.is_open_access = p.is_open_access
        publication.subtype = _get_subtype(p.subtype_code, p.subtype_description)
        publication.sponsor = _get_sponsor(p.sponsor_name)
        publication.funding_acr = _get_funding_acr(p.funding_acronym)
        publication.cited_by_count = p.cited_by_count
        publication.author_list = p.author_list

        if publication.publication_cover_date < current_app.config['HISTORIC_PUBLICATION_CUTOFF']:
            publication.validation_historic = True

        if source not in publication.sources:
            publication.sources.append(source)

        _add_keywords_to_publications(publication=publication, keyword_list=p.keywords)

    logging.info('add_publications: ended')
