from flask import current_app
from elsapy.elsclient import ElsClient
from elsapy.elssearch import ElsSearch

from academics.model import ScopusAuthor
from .model import AuthorSearch, Author


def _client():
    return ElsClient(current_app.config['SCOPUS_API_KEY'])


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
