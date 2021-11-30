from celery.utils.functional import first
from flask import current_app
from elsapy.elsclient import ElsClient
from elsapy.elssearch import ElsSearch
import academics
from academics.model import Academic, ScopusAuthor
from lbrc_flask.celery import celery
from .model import AuthorSearch, Author
from lbrc_flask.database import db


def _client():
    return ElsClient(current_app.config['SCOPUS_API_KEY'])


def updating():
    reservedq = list(celery.control.inspect().reserved().values())[0]
    scheduledq = list(celery.control.inspect().scheduled().values())[0]
    activeq = list(celery.control.inspect().active().values())[0]

    return len(reservedq) + len(scheduledq) + len(activeq) > 0


def author_search(search_string):
    auth_srch = ElsSearch(f'authlast({search_string}) AND affil(leicester)','author')
    auth_srch.execute(_client())

    existing_scopus_ids = [id for id, in ScopusAuthor.query.with_entities(ScopusAuthor.scopus_id).all()]

    result = []

    for r in auth_srch.results:
        a = AuthorSearch(r)

        if len(a.scopus_id) == 0:
            continue

        a.existing = a.scopus_id in existing_scopus_ids

        result.append(a)

    return result


def get_author(scopus_id):
    author = Author(scopus_id)

    if author.read(_client()):
        return author
    else:
        return None


def update_academics():
    _update_all_academics.delay()


@celery.task()
def _update_all_academics():
    for sa in ScopusAuthor.query.all():
        print(sa)


def add_authors_to_academic(scopus_ids, academic_id=None):
    _add_authors_to_academic.delay(scopus_ids, academic_id)

@celery.task()
def _add_authors_to_academic(scopus_ids, academic_id=None):
    academic = None

    if academic_id:
        academic = Academic.query.get(academic_id)
    
    if not academic:
        academic = Academic()

    for scopus_id in scopus_ids:
        author = get_author(scopus_id).get_scopus_author()
        author.academic = academic

        db.session.add(author)

    db.session.commit()
