from flask import current_app
from elsapy.elsclient import ElsClient
from elsapy.elssearch import ElsSearch
from .model import AuthorSearch, Author


def _client():
    return ElsClient(current_app.config['SCOPUS_API_KEY'])


def author_search(search_string):
    auth_srch = ElsSearch(f'authlast({search_string}) AND affil(leicester)','author')
    auth_srch.execute(_client())

    return filter(lambda a: len(a.scopus_id) > 0, [AuthorSearch(a) for a in auth_srch.results])


def get_author(scopus_id):
    author = Author(scopus_id)

    if author.read(_client()):
        return author
    else:
        return None
