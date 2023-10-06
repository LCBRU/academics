import logging
from time import sleep
from flask import current_app
from sqlalchemy import and_, or_, select
from academics.catalogs.utils import _add_keywords_to_publications, _add_sponsors_to_publications, _get_funding_acr, _get_journal, _get_sponsor, _get_subtype
from academics.model import Academic, AcademicPotentialSource, Affiliation, NihrAcknowledgement, NihrFundedOpenAccess, ScopusAuthor, ScopusPublication, Source, Subtype
from lbrc_flask.celery import celery
from .scopus import get_affiliation, get_els_author, get_scopus_publications, scopus_author_search
from lbrc_flask.database import db
from datetime import datetime
from lbrc_flask.logging import log_exception


def updating():
    result = Academic.query.filter(Academic.updating == True).count() > 0
    logging.info(f'updating: {result}')
    return result


def author_search(search_string):
    return scopus_author_search(search_string)


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


def update_single_academic(academic):
    logging.info('update_academic: started')

    for au in academic.sources:
        au.error = False
        db.session.add(au)
    
    academic.error = False
    academic.updating = True

    db.session.add(academic)

    db.session.commit()

    _update_all_academics.delay()

    logging.info('update_academic: ended')


def update_academics():
    logging.info('update_academics: started')
    if not updating():
        for academic in Academic.query.all():
            logging.info(f'Setting academic {academic.display_name} to be updated')

            for au in academic.sources:
                au.error = False
                db.session.add(au)

            academic.error = False
            academic.updating = True
            db.session.add(academic)

        db.session.commit()

        _update_all_academics.delay()

    logging.info('update_academics: ended')


@celery.task()
def _update_all_academics():
    logging.info('_update_all_academics: started')

    while True:
        a = Academic.query.filter(Academic.updating == 1 and Academic.error == 0).first()

        if not a:
            logging.info(f'No more academics to update')
            break

        try:
            _update_academic(a)

            a.set_name()
            a.updating = False
            db.session.add(a)

            db.session.commit()
        except Exception as e:
            logging.error(e)

            a.error = True
            db.session.add(a)

            db.session.commit()

            sleep(30)

    delete_orphan_publications()
    auto_validate()

    logging.info('_update_all_academics: Ended')


def _update_academic(academic):
    logging.info(f'Updating Academic {academic.display_name}')

    for sa in academic.sources:
        if sa.error:
            logging.info(f'Scopus Author in ERROR')
            continue

        try:
            els_author = get_els_author(sa.source_identifier)

            if els_author:
                els_author.update_scopus_author(sa)

                add_scopus_publications(els_author, sa)

                sa.affiliation = _get_affiliation(els_author.affiliation_id)

                sa.last_fetched_datetime = datetime.utcnow()
            else:
                sa.error = True
        except Exception as e:
            log_exception(e)
            logging.info(f'Setting Academic {academic.display_name} to be in error')
            sa.error = True
        finally:
            db.session.add(sa)


    _find_new_scopus_sources(academic)
    _ensure_all_academic_authors_are_proposed(academic)


def _get_affiliation(affiliation_id):
    logging.info('Starting _get_affiliation')

    existing = db.session.execute(select(Affiliation).where(Affiliation.catalog_identifier == affiliation_id)).scalar()

    if existing:
        return existing
    
    new = get_affiliation(affiliation_id)

    if new:
        return new.get_academic_affiliation()


def _find_new_scopus_sources(academic):
    logging.info(f'Finding new sources for {academic.display_name}')

    if len(academic.last_name.strip()) < 1:
        return

    new_source_identifiers = {a.source_identifier for a in author_search(academic.last_name)}

    logging.info(f'Found new sources: {new_source_identifiers}')

    for identifier in new_source_identifiers:
        if db.session.execute(
            select(db.func.count(AcademicPotentialSource.id))
            .where(AcademicPotentialSource.academic == academic)
            .where(AcademicPotentialSource.source.has(Source.source_identifier == identifier))
        ).scalar() > 0:
            continue

        sa = db.session.execute(
            select(ScopusAuthor).where(Source.source_identifier == identifier)
        ).scalar()

        if not sa:
            els_author = get_els_author(identifier)

            if els_author:
                af = _get_affiliation(els_author.affiliation_id)
                if af.is_leicester:
                    sa = els_author.get_scopus_author()
                    sa.affiliation = af

        if sa:
            aps = AcademicPotentialSource(
                academic=academic,
                source=sa,
            )

            db.session.add(sa)
            db.session.add(aps)
    
    db.session.commit()


def _ensure_all_academic_authors_are_proposed(academic):
    logging.info(f'Ensuring existing authors are proposed for {academic.display_name}')

    missing_sources = db.session.execute(
        select(ScopusAuthor)
        .where(~ScopusAuthor.potential_academics.any())
        .where(ScopusAuthor.academic == academic)
    ).scalars()

    logging.info(f'Missing sources found: {missing_sources}')

    for source in missing_sources:
        aps = AcademicPotentialSource(
            academic=academic,
            source=source,
        )

        db.session.add(aps)
    
    db.session.commit()


def add_authors_to_academic(source_identifiers, academic_id=None, theme_id=None):
    academic = None

    if academic_id:
        academic = db.session.get(Academic, academic_id)

    if not academic:
        academic = Academic(
            first_name='',
            last_name='',
            initialised=False,
            theme_id=theme_id,
        )

    academic.updating = True

    db.session.add(academic)
    db.session.commit()

    _add_authors_to_academic.delay(source_identifiers, academic_id=academic.id)


@celery.task()
def _add_authors_to_academic(source_identifiers, academic_id):
    logging.info('_add_authors_to_academic: started')

    academic = db.session.get(Academic, academic_id)

    for source_identifier in source_identifiers:
        els_author = get_els_author(source_identifier)

        if els_author:
            sa = els_author.get_scopus_author()
            sa.academic = academic

            add_scopus_publications(els_author, sa)

            sa.last_fetched_datetime = datetime.utcnow()
            db.session.add(sa)

    academic.set_name()
    academic.initialised = True
    academic.updating = False

    db.session.add(academic)
    db.session.commit()

    logging.info('_add_authors_to_academic: ended')


def delete_orphan_publications():
    for p in ScopusPublication.query.filter(~ScopusPublication.sources.any()):
        db.session.delete(p)
        db.session.commit()


def add_scopus_publications(els_author, scopus_author):
    logging.info('add_scopus_publications: started')

    for p in get_scopus_publications(els_author):
        publication = ScopusPublication.query.filter(ScopusPublication.scopus_id == p.catalog_identifier).one_or_none()

        if not publication:
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

        if scopus_author not in publication.sources:
            publication.sources.append(scopus_author)

        _add_keywords_to_publications(publication=publication, keyword_list=p.keywords)

    logging.info('add_scopus_publications: ended')
