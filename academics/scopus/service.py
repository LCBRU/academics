import logging
from flask import current_app
from elsapy.elsclient import ElsClient
from elsapy.elssearch import ElsSearch
from lbrc_flask.validators import parse_date
from academics.model import Academic, ScopusAuthor, ScopusPublication
from lbrc_flask.celery import celery
from .model import Abstract, AuthorSearch, Author
from lbrc_flask.database import db


def _client():
    return ElsClient(current_app.config['SCOPUS_API_KEY'])


def updating():
    return Academic.query.filter(Academic.updating == True).count() > 0


def author_search(search_string):
    auth_srch = ElsSearch(f'authlast({search_string}) AND affil(leicester)','author')
    auth_srch.execute(_client())

    logging.warn(auth_srch.results)

    existing_scopus_ids = [id for id, in ScopusAuthor.query.with_entities(ScopusAuthor.scopus_id).all()]

    result = []

    for r in auth_srch.results:
        a = AuthorSearch(r)

        if len(a.scopus_id) == 0:
            continue

        a.existing = a.scopus_id in existing_scopus_ids

        result.append(a)

    return result


def get_els_author(scopus_id):
    result = Author(scopus_id)

    if not result.read(_client()):
        return None

    return result


def add_scopus_publications(els_author, scopus_author):
    search_results = ElsSearch(query=f'au-id({els_author.scopus_id})', index='scopus')
    search_results.execute(_client(), get_all=True)

    for p in search_results.results:
        scopus_id = p.get(u'dc:identifier', ':').split(':')[1]

        publication = ScopusPublication.query.filter(ScopusPublication.scopus_id == scopus_id).one_or_none()

        if not publication:
            publication = ScopusPublication(scopus_id=scopus_id)

            href = None

            for h in p.get(u'link', ''):
                if h['@ref'] == 'scopus':
                    href = h['@href']

            publication.doi = p.get(u'prism:doi', '')
            publication.title = p.get(u'dc:title', '')
            publication.publication = p.get(u'prism:publicationName', '')
            publication.publication_cover_date = parse_date(p.get(u'prism:coverDate', ''))
            publication.href = href

            # Commented out because i've overshot the limit

            # abstract = Abstract(scopus_id)

            # if abstract.read(_client()) and abstract.abstract:
            #     logging.warn(f'abstract found - {abstract.abstract}')
            #     publication.abstract = abstract.abstract

        if scopus_author not in publication.scopus_authors:
            publication.scopus_authors.append(scopus_author)

        db.session.add(publication)


def update_academics():
    for academic in Academic.query.all():
        academic.updating = True
        db.session.add(academic)

    db.session.commit()

    _update_all_academics.delay()


@celery.task()
def _update_all_academics():
    logging.info('_update_all_academics: started')

    for sa in ScopusAuthor.query.all():
        els_author = get_els_author(sa.scopus_id)
        els_author.update_scopus_author(sa)

        add_scopus_publications(els_author, sa)

        db.session.add(sa)

    db.session.commit()

    for academic in Academic.query.all():
        academic.set_name()
        academic.updating = False
        db.session.add(academic)

    db.session.commit()

    logging.info('_update_all_academics: Ended')


def add_authors_to_academic(scopus_ids, academic_id=None, theme_id=None):
    academic = None

    if academic_id:
        academic = Academic.query.get(academic_id)

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

    academic = Academic.query.get(academic_id)
 
    for scopus_id in scopus_ids:
        els_author = get_els_author(scopus_id)
        sa = els_author.get_scopus_author()
        sa.academic = academic

        add_scopus_publications(els_author, sa)

        db.session.add(sa)

    academic.set_name()
    academic.initialised = True
    academic.updating = False

    db.session.add(academic)
    db.session.commit()

    logging.info('_add_authors_to_academic: ended')
