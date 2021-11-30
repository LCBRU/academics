import logging
from celery.utils.functional import first
from flask import current_app
from elsapy.elsclient import ElsClient
from elsapy.elssearch import ElsSearch
from academics.model import Academic, ScopusAuthor
from lbrc_flask.celery import celery
from .model import AuthorSearch, Author
from lbrc_flask.database import db


def _client():
    return ElsClient(current_app.config['SCOPUS_API_KEY'])


def updating():
    inspector = celery.control.inspect()

    reservedq = inspector.reserved() or {'': []}
    scheduledq = inspector.scheduled() or {'': []}
    activeq = inspector.active() or {'': []}

    reserved_jobs = list(reservedq.values())[0]
    scheduled_jobs = list(scheduledq.values())[0]
    active_jobs = list(activeq.values())[0]

    return len(reserved_jobs) + len(scheduled_jobs) + len(active_jobs) > 0


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
        author = get_author(sa.scopus_id)
        author.update_scopus_author(sa)

        db.session.add(sa)

    db.session.commit()

    for academic in Academic.query.all():
        _update_academic_name(academic_id=academic.id)


def add_authors_to_academic(scopus_ids, academic_id=None):
    _add_authors_to_academic.delay(scopus_ids, academic_id)


@celery.task()
def _add_authors_to_academic(scopus_ids, academic_id=None):
    academic = None

    if academic_id:
        academic = Academic.query.get(academic_id)
    
    if not academic:
        academic = Academic(first_name='', last_name='')

    for scopus_id in scopus_ids:
        author = get_author(scopus_id).get_scopus_author()
        author.academic = academic

        db.session.add(author)

    db.session.commit()

    _update_academic_name(academic_id=academic.id)


def _update_academic_name(academic_id):
    academic = Academic.query.get(academic_id)

    if not academic.scopus_authors:
        return

    top_author = sorted(academic.scopus_authors, key=lambda a: a.document_count, reverse=True)[0]

    academic.first_name = top_author.first_name
    academic.last_name = top_author.last_name

    db.session.add(academic)
    db.session.commit()
