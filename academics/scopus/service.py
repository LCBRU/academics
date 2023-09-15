import logging
import re
from time import sleep
from flask import current_app
from elsapy.elsclient import ElsClient
from elsapy.elssearch import ElsSearch
from lbrc_flask.validators import parse_date
from sqlalchemy import and_, or_
from academics.model import Academic, FundingAcr, Journal, Keyword, NihrAcknowledgement, NihrFundedOpenAccess, ScopusAuthor, ScopusPublication, Sponsor, Subtype
from lbrc_flask.celery import celery
from .model import Abstract, AuthorSearch, Author, DocumentSearch
from lbrc_flask.database import db
from datetime import datetime
from lbrc_flask.logging import log_exception


def _client():
    return ElsClient(current_app.config['SCOPUS_API_KEY'])


def updating():
    result = Academic.query.filter(Academic.updating == True).count() > 0
    logging.info(f'updating: {result}')
    return result


def author_search(search_string):
    re_orcid = re.compile(r'\d{4}-\d{4}-\d{4}-\d{4}$')

    if re_orcid.match(search_string):
        q = f'ORCID({search_string})'
    else:
        q = f'authlast({search_string})'

    auth_srch = ElsSearch(f'{q} AND affil(leicester)','author')
    auth_srch.execute(_client())

    existing_scopus_ids = [id for id, in ScopusAuthor.query.with_entities(ScopusAuthor.source_identifier).all()]

    result = []

    for r in auth_srch.results:
        a = AuthorSearch(r)

        if len(a.scopus_id) == 0:
            continue

        a.existing = a.scopus_id in existing_scopus_ids

        result.append(a)

    return result


def get_els_author(scopus_id):
    logging.info(f'Getting Scopus Author {scopus_id}')
    result = Author(scopus_id)

    if not result.read(_client()):
        logging.info(f'Scopus Author not read from Scopus')
        return None

    logging.info(f'Scopus Author details read from Scopus')
    return result


def add_scopus_publications(els_author, scopus_author):
    logging.info('add_scopus_publications: started')

    search_results = DocumentSearch(els_author)
    search_results.execute(_client(), get_all=True)

    for p in search_results.results:
        scopus_id = p.get(u'dc:identifier', ':').split(':')[1]

        publication = ScopusPublication.query.filter(ScopusPublication.scopus_id == scopus_id).one_or_none()

        if not publication:
            publication = ScopusPublication(scopus_id=scopus_id)

            abstract = Abstract(scopus_id)

            if abstract.read(_client()):
                publication.funding_text = abstract.funding_text
                _add_sponsors_to_publications(publication=publication, sponsor_names=abstract.funding_list)

        href = None

        for h in p.get(u'link', ''):
            if h['@ref'] == 'scopus':
                href = h['@href']

        publication.doi = p.get(u'prism:doi', '')
        publication.title = p.get(u'dc:title', '')
        publication.journal = _get_journal(p.get(u'prism:publicationName', ''))
        publication.publication_cover_date = parse_date(p.get(u'prism:coverDate', ''))
        publication.href = href
        publication.abstract = p.get(u'dc:description', '')
        publication.volume = p.get(u'prism:volume', '')
        publication.issue = p.get(u'prism:issueIdentifier', '')
        publication.pages = p.get(u'prism:pageRange', '')
        publication.is_open_access = p.get(u'openaccess', '0') == "1"
        publication.subtype = _get_subtype(p)
        publication.sponsor = _get_sponsor(p)
        publication.funding_acr = _get_funding_acr(p)
        publication.cited_by_count = int(p.get(u'citedby-count', '0'))
        publication.author_list = _get_author_list(p.get('author', []))

        if publication.publication_cover_date < current_app.config['HISTORIC_PUBLICATION_CUTOFF']:
            publication.validation_historic = True

        if scopus_author not in publication.sources:
            publication.sources.append(scopus_author)

        _add_keywords_to_publications(publication=publication, keyword_list=p.get(u'authkeywords', ''))

        db.session.add(publication)

    logging.info('add_scopus_publications: ended')


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


def _get_journal(journal_name):
    journal_name = (journal_name or '').lower().strip()

    if not journal_name:
        return None

    result = Journal.query.filter(Journal.name == journal_name).one_or_none()

    if not result:
        result = Journal(name=journal_name)
        db.session.add(result)

    return result


def _get_subtype(p):
    code = p.get(u'subtype', '')
    description = p.get(u'subtypeDescription', '')

    if not code:
        return None

    result = Subtype.query.filter(Subtype.code == code).one_or_none()

    if not result:
        result = Subtype(code=code, description=description)
        db.session.add(result)

    return result


def _get_sponsor(p):
    name = p.get(u'fund-sponsor', '')

    if not name:
        return None

    result = Sponsor.query.filter(Sponsor.name == name).one_or_none()

    if not result:
        result = Sponsor(name=name)
        db.session.add(result)

    return result


def _get_funding_acr(p):
    name = p.get(u'fund-acr', '')

    if not name:
        return None

    result = FundingAcr.query.filter(FundingAcr.name == name).one_or_none()

    if not result:
        result = FundingAcr(name=name)
        db.session.add(result)

    return result


def _get_nihr_acknowledgement(pub):
    if pub.is_nihr_acknowledged:
        return NihrAcknowledgement.get_instance_by_name(NihrAcknowledgement.NIHR_ACKNOWLEDGED)


def _get_nihr_funded_open_access(pub):
    if pub.all_nihr_acknowledged and pub.is_open_access:
        return NihrFundedOpenAccess.get_instance_by_name(NihrFundedOpenAccess.NIHR_FUNDED)


def _get_author_list(authors):
    author_names = [a['authname'] for a in authors]
    unique_author_names = list(dict.fromkeys(filter(len, author_names)))
    return ', '.join(unique_author_names)


def _add_keywords_to_publications(publication, keyword_list):
    publication.keywords.clear()

    for k in keyword_list.split('|'):
        keyword_word = k.strip().lower()

        if not keyword_word:
            continue

        keyword = Keyword.query.filter(Keyword.keyword == keyword_word).one_or_none()

        if not keyword:
            keyword = Keyword(keyword=keyword_word)
            db.session.add(keyword)
        
        publication.keywords.add(keyword)


def _add_sponsors_to_publications(publication, sponsor_names):
    publication.keywords.clear()

    for name in sponsor_names:
        if not name:
            continue

        sponsor = Sponsor.query.filter(Sponsor.name == name).one_or_none()

        if not sponsor:
            sponsor = Sponsor(name=name)
            db.session.add(sponsor)
        
        publication.sponsors.add(sponsor)


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
            logging.info(f'Setting academic {academic.full_name} to be updated')

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
    logging.info(f'Updating Academic {academic.full_name}')

    _find_new_scopus_sources(academic)

    for sa in academic.sources:
        logging.info(f'A')
        if sa.error:
            logging.info(f'Scopus Author in ERROR')
            continue

        try:
            logging.info(f'B')
            els_author = get_els_author(sa.source_identifier)
            logging.info(f'C')
            els_author.update_scopus_author(sa)

            logging.info(f'D')
            add_scopus_publications(els_author, sa)

            logging.info(f'E')
            sa.last_fetched_datetime = datetime.utcnow()
            logging.info(f'F')
        except Exception as e:
            logging.info(f'G')
            log_exception(e)
            logging.info(f'Setting Academic {academic.full_name} to be in error')
            sa.error = True
        finally:
            db.session.add(sa)


def _find_new_scopus_sources(academic):
    logging.info(f'Finding new sources for {academic.full_name}')

    for a in author_search(academic.last_name):
        logging.info(f'Found new source: {a}')


def add_authors_to_academic(scopus_ids, academic_id=None, theme_id=None):
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

    _add_authors_to_academic.delay(scopus_ids, academic_id=academic.id)


@celery.task()
def _add_authors_to_academic(scopus_ids, academic_id):
    logging.info('_add_authors_to_academic: started')

    academic = db.sessio.get(Academic, academic_id)

    for scopus_id in scopus_ids:
        els_author = get_els_author(scopus_id)
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
