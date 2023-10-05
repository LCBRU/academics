from dataclasses import dataclass
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


def add_scopus_publications(els_author, scopus_author):
    logging.info('add_scopus_publications: started')

    search_results = DocumentSearch(els_author)
    search_results.execute(_client(), get_all=True)

    for p in search_results.results:
        scopus_id = p.get(u'dc:identifier', ':').split(':')[1]

        publication = ScopusPublication.query.filter(ScopusPublication.scopus_id == scopus_id).one_or_none()

        if not publication:
            publication = ScopusPublication(scopus_id=scopus_id)

            abstract = Abstract(scopus_id)

            if abstract.read(_client()):
                publication.funding_text = abstract.funding_text
                _add_sponsors_to_publications(publication=publication, sponsor_names=abstract.funding_list)

        href = None

        for h in p.get(u'link', ''):
            if h['@ref'] == 'scopus':
                href = h['@href']

        publication.doi = p.get(u'prism:doi', '')
        publication.title = p.get(u'dc:title', '')
        publication.journal = _get_journal(p.get(u'prism:publicationName', ''))
        publication.publication_cover_date = parse_date(p.get(u'prism:coverDate', ''))
        publication.href = href
        publication.abstract = p.get(u'dc:description', '')
        publication.volume = p.get(u'prism:volume', '')
        publication.issue = p.get(u'prism:issueIdentifier', '')
        publication.pages = p.get(u'prism:pageRange', '')
        publication.is_open_access = p.get(u'openaccess', '0') == "1"
        publication.subtype = _get_subtype(p)
        publication.sponsor = _get_sponsor(p)
        publication.funding_acr = _get_funding_acr(p)
        publication.cited_by_count = int(p.get(u'citedby-count', '0'))
        publication.author_list = _get_author_list(p.get('author', []))

        if publication.publication_cover_date < current_app.config['HISTORIC_PUBLICATION_CUTOFF']:
            publication.validation_historic = True

        if scopus_author not in publication.sources:
            publication.sources.append(scopus_author)

        _add_keywords_to_publications(publication=publication, keyword_list=p.get(u'authkeywords', ''))

        db.session.add(publication)

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


def _get_author_list(authors):
    author_names = [a['authname'] for a in authors]
    unique_author_names = list(dict.fromkeys(filter(len, author_names)))
    return ', '.join(unique_author_names)


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
