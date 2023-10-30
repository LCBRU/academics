from dataclasses import dataclass
import pyalex
import logging

from sqlalchemy import select
from academics.config import Config
from pyalex import Authors, Works, Institutions
from itertools import chain
from flask import current_app
from lbrc_flask.database import db

from academics.model import Academic, OpenAlexAuthor, Affiliation


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
        
        i = Institutions()[a['last_known_institution']['id']]
        print(i['geo'])

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

    existing = set(db.session.execute(
        select(OpenAlexAuthor.source_identifier)
    ).scalars())

    if academic.orcid:
        authors.extend(_get_for_orcid(academic.orcid))

    result = []

    for a in [a for a in authors if _get_open_alex_id_from_href(a.get('id', '')) not in existing]:
        institution_id = _get_open_alex_id_from_href(a.get('last_known_institution', {}).get('id', ''))
        i = Institutions()[institution_id]

        print(i)

        result.append(
            AuthorData(
                catalog=OPEN_ALEX_CATALOG,
                catalog_identifier=_get_open_alex_id_from_href(a.get('id', '')),
                orcid=a.get('orcid', None),
                display_name=a.get('display_name', ''),
                href=a.get('id', ''),
                affiliation_identifier=institution_id,
                affiliation_name=i.get('display_name', ''),
                affiliation_address=i.get('geo', {}).get('city', ''),
                affiliation_country=i.get('geo', {}).get('country', ''),
                citation_count=a.get('cited_by_count', None),
                document_count=a.get('works_count', None),
                h_index=a.get('works_count', {}).get('h_index', None),
            )
        )

    print(result)
    return result

def _get_open_alex_id_from_href(href):
    _, result = href.rsplit('/', 1)
    return result

def _get_for_orcid(orcid):
    q = Authors().filter(orcid=orcid)
    return chain(*q.paginate(per_page=200))


@dataclass
class AuthorData:
    catalog: str
    catalog_identifier: str
    orcid: str
    display_name: str
    href: str
    affiliation_identifier: str
    affiliation_name: str
    affiliation_address: str
    affiliation_country: str
    citation_count: int
    document_count: int
    h_index: float

    @property
    def is_leicester(self):
        return 'leicester' in self.affiliation_summary.lower()

    @property
    def affiliation_summary(self):
        return ', '.join(filter(None, [self.affiliation_name, self.affiliation_address, self.affiliation_country]))

    def get_new_source(self):
        result = OpenAlexAuthor()
        self.update_source(result)
        return result

    def update_source(self, source):
        source.source_identifier = self.catalog_identifier
        source.orcid = self.orcid
        source.first_name = self.first_name
        source.last_name = self.last_name
        source.display_name = self.display_name
        source.href = self.href            
        source.citation_count = self.citation_count
        source.document_count = self.document_count
        source.h_index = self.h_index

        source.affiliation =self.get_affiliation()


    def get_affiliation(self):
        result = db.session.execute(
            select(Affiliation).where(
                Affiliation.catalog_identifier == self.affiliation_identifier
            ).where(
                Affiliation.catalog == OPEN_ALEX_CATALOG
            )
        ).scalar()

        if not result:
            result = Affiliation(catalog_identifier=self.affiliation_identifier)
        
            result.name = self.affiliation_name
            result.address = self.affiliation_address
            result.country = self.affiliation_country

            result.catalog = OPEN_ALEX_CATALOG

        return result
