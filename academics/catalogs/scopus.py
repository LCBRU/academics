from dataclasses import dataclass
from datetime import date
import logging
import re
from elsapy.elssearch import ElsSearch
from elsapy.elsprofile import ElsAuthor, ElsAffil
from academics.catalogs.utils import _add_keywords_to_publications, _add_sponsors_to_publications, _get_funding_acr, _get_journal, _get_sponsor, _get_subtype
from academics.model import ScopusAuthor, Affiliation as AcaAffil
from elsapy.elsdoc import AbsDoc
from elsapy.elsclient import ElsClient
from flask import current_app
from sqlalchemy import select
from lbrc_flask.database import db
from academics.model import Affiliation, ScopusAuthor, ScopusPublication
from lbrc_flask.validators import parse_date


def _client():
    return ElsClient(current_app.config['SCOPUS_API_KEY'])


def _get_scopus_publication_link(p):
    for h in p.get(u'link', ''):
        if h['@ref'] == 'scopus':
            return h['@href']


def get_scopus_publications(els_author):
    logging.info('get_scopus_publications: started')

    search_results = DocumentSearch(els_author)
    search_results.execute(_client(), get_all=True)

    return [
        PublicationData(
            catalog='scopus',
            catalog_identifier=p.get(u'dc:identifier', ':').split(':')[1],
            href=_get_scopus_publication_link(p),
            doi=p.get(u'prism:doi', ''),
            title=p.get(u'dc:title', ''),
            journal_name=p.get(u'prism:publicationName', ''),
            publication_cover_date=parse_date(p.get(u'prism:coverDate', '')),
            abstract_text=p.get(u'dc:description', ''),
            volume=p.get(u'prism:volume', ''),
            issue=p.get(u'prism:issueIdentifier', ''),
            pages=p.get(u'prism:pageRange', ''),
            subtype_code=p.get(u'subtype', ''),
            subtype_description=p.get(u'subtypeDescription', ''),
            sponsor_name=p.get(u'fund-sponsor', ''),
            funding_acronym=p.get(u'fund-acr', ''),
            cited_by_count=int(p.get(u'citedby-count', '0')),
            author_list=', '.join(list(dict.fromkeys(filter(len, [a['authname'] for a in p.get('author', [])])))),
            keywords=p.get(u'authkeywords', ''),
            is_open_access=p.get(u'openaccess', '0') == "1",
        ) for p in search_results.results
    ]


def add_scopus_publications(els_author, scopus_author):
    logging.info('add_scopus_publications: started')

    for p in get_scopus_publications(els_author):
        publication = ScopusPublication.query.filter(ScopusPublication.scopus_id == p.catalog_identifier).one_or_none()

        if not publication:
            publication.funding_text = p.abstract.funding_text
            _add_sponsors_to_publications(
                publication=publication,
                sponsor_names=p.abstract.funding_list,
            )

        db.session.add(publication)

        publication.doi = p.doi
        publication.title = p.title
        publication.journal = _get_journal(p.journal_name)
        publication.publication_cover_date = p.publication_cover_date
        publication.href = p.href
        publication.abstract = p.abstract_text
        publication.volume = p.volume
        publication.issue = p.issue
        publication.pages = p.pages
        publication.is_open_access = p.is_open_access
        publication.subtype = _get_subtype(p.subtype_code, p.subtype_description)
        publication.sponsor = _get_sponsor(p.sponsor_name)
        publication.funding_acr = _get_funding_acr(p.funding_acronym)
        publication.cited_by_count = p.cited_by_count
        publication.author_list = p.author_list

        if publication.publication_cover_date < current_app.config['HISTORIC_PUBLICATION_CUTOFF']:
            publication.validation_historic = True

        if scopus_author not in publication.sources:
            publication.sources.append(scopus_author)

        _add_keywords_to_publications(publication=publication, keyword_list=p.keywords)

    logging.info('add_scopus_publications: ended')


def get_els_author(source_identifier):
    logging.info(f'Getting Scopus Author {source_identifier}')
    result = Author(source_identifier)

    if not result.read(_client()):
        logging.info(f'Scopus Author not read from Scopus')
        return None

    logging.info(f'Scopus Author details read from Scopus')
    return result


def scopus_author_search(search_string):
    re_orcid = re.compile(r'\d{4}-\d{4}-\d{4}-\d{4}$')

    if re_orcid.match(search_string):
        q = f'ORCID({search_string})'
    else:
        q = f'authlast({search_string})'

    auth_srch = ElsSearch(f'{q} AND affil(leicester)','author')
    auth_srch.execute(_client())

    existing_source_identifiers = set(db.session.execute(
        select(ScopusAuthor.source_identifier)
        .where(ScopusAuthor.academic_id != None)
    ).scalars())

    result = []

    for r in auth_srch.results:
        a = AuthorSearch(r)

        if len(a.source_identifier) == 0:
            continue

        a.existing = a.source_identifier in existing_source_identifiers

        result.append(a)

    return result


class Author(ElsAuthor):
    def __init__(self, source_identifier):
        self.source_identifier = source_identifier
        super().__init__(author_id=self.source_identifier)

    @property
    def href(self):
        for h in  self.data.get(u'coredata', {}).get(u'link', ''):
            if h['@rel'] == 'scopus-author':
                return h['@href']

    @property
    def orcid(self):
        return self.data.get(u'coredata', {}).get(u'orcid', '')

    @property
    def citation_count(self):
        return self.data.get(u'coredata', {}).get(u'citation-count', '')

    @property
    def document_count(self):
        return self.data.get(u'coredata', {}).get(u'document-count', '')

    @property
    def affiliation_id(self):
        return self.data.get(u'affiliation-current', {}).get(u'@id', '')

    @property
    def h_index(self):
        return self.data.get(u'h-index', None)

    def read(self, client):
        try:
            result = super().read(client)
            super().read_metrics(client)
        except Exception:
            logging.info('Error reading Scopus data')
            return None
        
        if self.data is None:
            logging.info('No error reading Scopus data, but data is still None')
            return None

        if self.affiliation_id:
            self.affiliation = Affiliation(affiliation_id=self.affiliation_id)
            self.affiliation.read(client)
        else:
            self.affiliation = None

        return result

    def update_scopus_author(self, scopus_author):
        scopus_author.source_identifier = self.source_identifier
        scopus_author.orcid = self.orcid
        scopus_author.first_name = self.first_name
        scopus_author.last_name = self.last_name
        scopus_author.display_name = ' '.join(filter(None, [self.first_name, self.last_name]))

        scopus_author.citation_count = self.citation_count
        scopus_author.document_count = self.document_count
        scopus_author.h_index = self.h_index
        scopus_author.href = self.href

    def get_scopus_author(self):
        result = ScopusAuthor()
        self.update_scopus_author(result)
        return result


def get_affiliation(affiliation_id):
    result = Affiliation(affiliation_id=affiliation_id)
    if result.read(_client()):
        return result
    else:
        return None


class Affiliation(ElsAffil):
    def __init__(self, affiliation_id):
        self.affiliation_id = affiliation_id
        super().__init__(affil_id=affiliation_id)

    @property
    def name(self):
        return self.data.get(u'affiliation-name', '')

    @property
    def address(self):
        return ', '.join(filter(None, [self.data.get(u'address', ''), self.data.get(u'city', '')]))

    @property
    def country(self):
        return self.data.get(u'country', '')
    
    def get_academic_affiliation(self):
        return AcaAffil(
            catalog='scopus',
            catalog_identifier=self.affiliation_id,
            name=self.name,
            address=self.address,
            country=self.country,
        )


class Abstract(AbsDoc):
    def __init__(self, scopus_id):
        self.scopus_id = scopus_id
        super().__init__(scp_id=self.scopus_id)

    @property
    def funding_list(self):
        if not self.data:
            return set()

        result = set()

        funding_section = self.data.get('item', {}).get('xocs:meta', {}).get('xocs:funding-list', {}).get('xocs:funding', None)

        if type(funding_section) is list:

            for f in funding_section:
                if f.get('xocs:funding-agency-matched-string', None):
                    result.add(f.get('xocs:funding-agency-matched-string', None))
                if f.get('xocs:funding-agency', None):
                    result.add(f.get('xocs:funding-agency', None))

        elif type(funding_section) is dict:
            result.add(funding_section.get('xocs:funding-agency', None))

        return result

    @property
    def funding_text(self):
        if not self.data:
            return ''

        funding_text = self.data.get('item', {}).get('xocs:meta', {}).get('xocs:funding-list', {}).get('xocs:funding-text', '')

        if type(funding_text) is list:
            return '\n'.join([t.get('$', '') for t in funding_text])
        else:
            return funding_text

    def read(self, client):
        try:
            super().read(client)
            return True
        except Exception as e:
            logging.error(e)
            return False


class DocumentSearch(ElsSearch):
    def __init__(self, author):
        super().__init__(query=f'au-id({author.source_identifier})', index='scopus')
        self._uri += '&view=complete'


@dataclass
class AuthorSearch():

    source_identifier: str
    first_name: str
    last_name: str
    affiliation_id: str
    affiliation_name: str
    existing : bool = False
    
    def __init__(self, data):
        self.source_identifier = data.get(u'dc:identifier', ':').split(':')[1]
        self.first_name = data.get(u'preferred-name', {}).get(u'given-name', '')
        self.last_name = data.get(u'preferred-name', {}).get(u'surname', '')
        self.affiliation_id = data.get(u'affiliation-current', {}).get(u'affiliation-id', '')
        self.affiliation_name = data.get(u'affiliation-current', {}).get(u'affiliation-name', '')

    @property
    def full_name(self):
        return ', '.join(
            filter(len, [
                self.first_name,
                self.last_name,
            ])
        )


@dataclass
class PublicationData():
    catalog: str
    catalog_identifier: str
    href: str
    doi: str
    title: str
    journal_name: str
    publication_cover_date: date
    abstract_text: str
    volume: str
    issue: str
    pages: str
    subtype_code: str
    subtype_description: str
    sponsor_name: str
    funding_acronym: str
    cited_by_count: int
    author_list: str
    keywords: str
    is_open_access : bool = False
    _abstract: Abstract

    @property
    def abstract(self):
        if not self._abstract:
            self._abstract = Abstract(self.catalog_identifier)
            self._abstract.read(_client())

        return self._abstract