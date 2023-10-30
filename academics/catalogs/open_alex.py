import pyalex
import logging
from academics.config import Config
from pyalex import Authors, Works
from itertools import chain
from flask import current_app

from academics.model import Academic


OPEN_ALEX_CATALOG = 'open alex'


def get_open_alex():
    config = Config()
    pyalex.config.email = config.OPEN_ALEX_EMAIL

    # q = Authors().search_filter(display_name="mccann")
    # q = Authors().filter(orcid="0000-0002-5542-8448")
    q = Authors().filter(scopus="7005783434")
    # # # works = Works().filter(**{"author.id": author['id']}).filter(publication_year="2022").get()

    for a in chain(*q.paginate(per_page=200)):
        print(a['id'], a["display_name"])
        print(a["display_name"].strip().rsplit(maxsplit=1))
        print(a.keys())
        if a['summary_stats']:
            print(a['summary_stats'].keys())
            print(a['summary_stats'])
        if a['last_known_institution']:
            print(a['last_known_institution'].keys())
            print(a['last_known_institution'])
        # if a:
        #     if a.get('last_known_institution', None):
        #         if 'leicester' in a.get('last_known_institution', {}).get('display_name', '').lower():
        #             print(a['id'], a["display_name"], a['last_known_institution']['display_name'])


def open_alex_similar_authors(academic: Academic):
    if not current_app.config['OPEN_ALEX_ENABLED']:
        print(current_app.config['OPEN_ALEX_ENABLED'])
        logging.info('OpenAlex Not Enabled')
        return []

    authors = []

    if academic.orcid:
        authors.extend(_get_for_orcid(academic.orcid))

    print(authors)

    return []

def _get_for_orcid(orcid):
    q = Authors().filter(orcid=orcid)
    return chain(*q.paginate(per_page=200))


    # auth_srch = ElsSearch(f'{q} AND affil(leicester)','author')
    # auth_srch.execute(_client())

    # existing_source_identifiers = set(db.session.execute(
    #     select(ScopusAuthor.source_identifier)
    #     .where(ScopusAuthor.academic_id != None)
    # ).scalars())

    # result = []

    # for r in auth_srch.results:
    #     href = ''
    #     for h in r.get(u'coredata', {}).get(u'link', ''):
    #         if h['@rel'] == 'scopus-author':
    #             href = h['@href']
        
    #     affiliation_identifier = r.get(u'affiliation-current', {}).get(u'affiliation-id', '')

    #     sa = ScopusAffiliation(affiliation_identifier).get_affiliation()

    #     a = AuthorData(
    #         catalog=SCOPUS_CATALOG,
    #         catalog_identifier=r.get(u'dc:identifier', ':').split(':')[1],
    #         orcid=r.get(u'coredata', {}).get(u'orcid', ''),
    #         first_name=r.get(u'preferred-name', {}).get(u'given-name', ''),
    #         last_name=r.get(u'preferred-name', {}).get(u'surname', ''),
    #         href=href,
    #         affiliation_identifier=affiliation_identifier,
    #         affiliation_name=sa.name,
    #         affiliation_address=sa.address,
    #         affiliation_country=sa.country,
    #     )

    #     if len(a.catalog_identifier) == 0:
    #         continue

    #     a.existing = a.catalog_identifier in existing_source_identifiers

    #     result.append(a)

    # return result
