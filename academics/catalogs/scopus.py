from dataclasses import dataclass
from datetime import date, datetime
import logging
import requests
import time
import re
import json
from elsapy.elssearch import ElsSearch
from elsapy.elsprofile import ElsAuthor, ElsAffil
from academics.model import ScopusAuthor, Affiliation as AcaAffil
from elsapy.elsdoc import AbsDoc
from elsapy.elsclient import ElsClient
from flask import current_app
from sqlalchemy import select
from lbrc_flask.database import db
from lbrc_flask.logging import log_exception
from academics.model import Affiliation, ScopusAuthor
from lbrc_flask.validators import parse_date
from elsapy import version

class ScopusClient(ElsClient):
    # class variables
    __url_base = "https://api.elsevier.com/"    ## Base URL for later use
    __user_agent = "elsapy-v%s" % version       ## Helps track library use
    __min_req_interval = 15                     ## Min. request interval in sec
    __ts_last_req = time.time()                 ## Tracker for throttling
 

    def exec_request(self, URL):
        """Sends the actual request; returns response."""

        ## Throttle request, if need be
        interval = time.time() - self.__ts_last_req
        if (interval < self.__min_req_interval):
            time.sleep( self.__min_req_interval - interval )
        
        ## Construct and execute request
        headers = {
            "X-ELS-APIKey"  : self.api_key,
            "User-Agent"    : self.__user_agent,
            "Accept"        : 'application/json'
            }
        if self.inst_token:
            headers["X-ELS-Insttoken"] = self.inst_token
        logging.info('Sending GET request to ' + URL)
        r = requests.get(
            URL,
            headers = headers
            )
        self.__ts_last_req = time.time()
        self._status_code=r.status_code
        if r.status_code == 200:
            next_allowed = datetime.fromtimestamp(int(r.headers.get("X-RateLimit-Reset", 0)))
            rate_limit = r.headers.get("X-RateLimit-Limit", '')
            rate_limit_remaining = r.headers.get("X-RateLimit-Remaining", '')

            logging.info(f'Request Successful')
            logging.info(f'X-RateLimit-Limit: {rate_limit}')
            logging.info(f'X-RateLimit-Remaining: {rate_limit_remaining}')
            logging.info(f'X-RateLimit-Reset: {next_allowed}')

            self._status_msg='data retrieved'
            return json.loads(r.text)
        elif r.status_code == 429:
            next_allowed = datetime.fromtimestamp(int(r.headers.get("X-RateLimit-Reset", 0)))
            logging.warn(f'QUOTA EXCEEDED: Next Request Allowed {next_allowed}')
            self._status_msg="HTTP " + str(r.status_code) + " Error from " + URL + " and using headers " + str(headers) + ": " + r.text
            raise requests.HTTPError("HTTP " + str(r.status_code) + " Error from " + URL + "\nand using headers " + str(headers) + ":\n" + r.text)
        else:
            self._status_msg="HTTP " + str(r.status_code) + " Error from " + URL + " and using headers " + str(headers) + ": " + r.text
            raise requests.HTTPError("HTTP " + str(r.status_code) + " Error from " + URL + "\nand using headers " + str(headers) + ":\n" + r.text)


def _client():
    return ScopusClient(current_app.config['SCOPUS_API_KEY'])


def _get_scopus_publication_link(p):
    for h in p.get(u'link', ''):
        if h['@ref'] == 'scopus':
            return h['@href']


def get_affiliation(affiliation_id):
    if not current_app.config['SCOPUS_ENABLED']:
        print(current_app.config['SCOPUS_ENABLED'])
        logging.info('SCOPUS Not Enabled')
        return None

    result = Affiliation(affiliation_id=affiliation_id)
    result.read(_client())
    return result


def get_scopus_publications(els_author):
    logging.info('get_scopus_publications: started')

    if not current_app.config['SCOPUS_ENABLED']:
        print(current_app.config['SCOPUS_ENABLED'])
        logging.info('SCOPUS Not Enabled')
        return []

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


def get_els_author(source_identifier):
    logging.info(f'Getting Scopus Author {source_identifier}')

    if not current_app.config['SCOPUS_ENABLED']:
        print(current_app.config['SCOPUS_ENABLED'])
        logging.info('SCOPUS Not Enabled')
        return None

    result = Author(source_identifier)

    if not result.read(_client()):
        logging.info(f'Scopus Author not read from Scopus')
        return None

    logging.info(f'Scopus Author details read from Scopus')
    return result


def scopus_author_search(search_string):
    if not current_app.config['SCOPUS_ENABLED']:
        print(current_app.config['SCOPUS_ENABLED'])
        logging.info('SCOPUS Not Enabled')
        return []

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
        except Exception as e:
            log_exception(e)
            logging.info('Error reading Scopus data')
            return None
        
        if self.data is None:
            logging.info('No error reading Scopus data, but data is still None')
            return None

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


class Affiliation(ElsAffil):
    def __init__(self, affiliation_id):
        self.affiliation_id = affiliation_id
        super().__init__(affil_id=affiliation_id)

    @property
    def name(self):
        if self.data:
            return self.data.get(u'affiliation-name', '')
        else:
            return ''

    @property
    def address(self):
        if self.data:
            return ', '.join(filter(None, [self.data.get(u'address', ''), self.data.get(u'city', '')]))
        else:
            return ''

    @property
    def country(self):
        if self.data:
            return self.data.get(u'country', '')
        else:
            return ''
    
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
        q = f'au-id({author.source_identifier})'

        if not current_app.config['LOAD_OLD_PUBLICATIONS']:
            q = f'{q} AND PUBYEAR > {datetime.date.today().year - 1}'

        super().__init__(query=q, index='scopus')
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
    _abstract: Abstract = None
    is_open_access : bool = False

    @property
    def abstract(self):
        if not self._abstract:
            self._abstract = Abstract(self.catalog_identifier)
            self._abstract.read(_client())

        return self._abstract