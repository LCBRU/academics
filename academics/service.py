from flask import current_app
from elsapy.elsclient import ElsClient
from elsapy.elssearch import ElsSearch
from academics.model import ScopusAuthor


def author_search(search_string):
    client = ElsClient(current_app.config['SCOPUS_API_KEY'])

    auth_srch = ElsSearch(f'authlast({search_string}) AND affil(leicester)','author')
    auth_srch.execute(client)

    return [ScopusAuthor(a) for a in auth_srch.results]
