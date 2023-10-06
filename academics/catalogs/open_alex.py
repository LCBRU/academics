import pyalex
from academics.config import Config
from pyalex import Authors, Works
from itertools import chain


def get_open_alex():
    config = Config()
    pyalex.config.email = config.OPEN_ALEX_EMAIL

    print(Authors().search_filter(display_name="gerry mccann").count())
    q = Authors().search_filter(display_name="gerry mccann")
    # # # works = Works().filter(**{"author.id": author['id']}).filter(publication_year="2022").get()

    for a in chain(*q.paginate(per_page=200)):
        print(a['id'], a["display_name"])
        print(a["display_name"].strip().rsplit(maxsplit=1))
        if a['last_known_institution']:
            print(a['last_known_institution'].keys())
            print(a['last_known_institution'])
        # if a:
        #     if a.get('last_known_institution', None):
        #         if 'leicester' in a.get('last_known_institution', {}).get('display_name', '').lower():
        #             print(a['id'], a["display_name"], a['last_known_institution']['display_name'])
