from datetime import date, datetime
import logging
from random import choice, randint
import requests
import time
import re
import json
from elsapy.elssearch import ElsSearch
from elsapy.elsprofile import ElsAuthor, ElsAffil
from academics.catalogs.data_classes import AffiliationData, AuthorData, PublicationData
from elsapy.elsdoc import AbsDoc
from elsapy.elsclient import ElsClient
from flask import current_app
from sqlalchemy import select
from lbrc_flask.database import db
from lbrc_flask.logging import log_exception
from lbrc_flask.validators import parse_date
from lbrc_flask.data_conversions import ensure_list, convert_int_nullable
from elsapy import version
from functools import cache
from cachetools import cached, TTLCache
from academics.model.academic import Academic, Source

from academics.model.catalog import CATALOG_SCOPUS


class ResourceNotFoundException(Exception):
    pass


class ScopusClient(ElsClient):
    # class variables
    __url_base = "https://api.elsevier.com/"    ## Base URL for later use
    __user_agent = "elsapy-v%s" % version       ## Helps track library use
    __min_req_interval = 1                      ## Min. request interval in sec
    __ts_last_req = time.time()                 ## Tracker for throttling
 

    @cached(cache=TTLCache(maxsize=1024, ttl=60*60))
    def exec_request(self, URL):
        """Sends the actual request; returns response."""

        ## Throttle request, if need be
        interval = time.time() - self.__ts_last_req

        logging.debug(f'Checking throttle - Time: {time.time()}; Last Request: {self.__ts_last_req}; Interval: {interval}')
        if (interval < self.__min_req_interval):
            logging.debug(f'Throttle Start: {time.time()}')
            time.sleep( self.__min_req_interval - interval )
            logging.debug(f'Throttle End: {time.time()}')
        
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

            logging.debug(f'Request Successful')
            logging.debug(f'X-RateLimit-Limit: {rate_limit}')
            logging.debug(f'X-RateLimit-Remaining: {rate_limit_remaining}')
            logging.debug(f'X-RateLimit-Reset: {next_allowed}')

            self._status_msg='data retrieved'
            return json.loads(r.text)
        elif r.status_code == 429:
            next_allowed = datetime.fromtimestamp(int(r.headers.get("X-RateLimit-Reset", 0)))
            logging.warn(f'QUOTA EXCEEDED: Next Request Allowed {next_allowed}')
            self._status_msg="HTTP " + str(r.status_code) + " Error from " + URL + " and using headers " + str(headers) + ": " + r.text
            raise requests.HTTPError("HTTP " + str(r.status_code) + " Error from " + URL + "\nand using headers " + str(headers) + ":\n" + r.text)
        elif r.status_code == 404:
            logging.warn(f'Resource not found: for URL {URL}')
            raise ResourceNotFoundException(f'Resource not found: for URL {URL}')
        else:
            self._status_msg="HTTP " + str(r.status_code) + " Error from " + URL + " and using headers " + str(headers) + ": " + r.text
            raise requests.HTTPError("HTTP " + str(r.status_code) + " Error from " + URL + " and using headers " + str(headers) + ": " + r.text)


@cache
def _client():
    return ScopusClient(current_app.config['SCOPUS_API_KEY'])


def _get_scopus_publication_link(p):
    for h in p.get(u'link', ''):
        if h.get('@rel', '') == 'scopus' or h.get('@ref', '') == 'scopus':
            return h['@href']


def get_scopus_publication_data(scopus_id=None, doi=None, log_data=False):
    logging.debug('started')

    if not current_app.config['SCOPUS_ENABLED']:
        logging.warn('SCOPUS Not Enabled')
        return []
    
    a = Abstract(scopus_id, doi)
    a.read(_client())

    if not a.data:
        logging.info(f'No publication for {scopus_id=}; {doi=}')
        return None

    if log_data:
        logging.info(a.data)
        with open('rich_dump.json', 'w') as f:
            f.write(json.dumps(a.data, sort_keys=True, indent=4))

    id = ((a.data.get('coredata', {}) or {}).get(u'dc:identifier', ':') or ':').split(':')[1]

    if not id:
        logging.info(f'No publication for {scopus_id=}; {doi=}')
        return None

    publication_date = a.data.get('item', {}).get('bibrecord', {}).get('head', {}).get('source', {}).get('publicationdate', {})
    date_text = publication_date.get('date-text', '')
    if '$' in date_text:
        date_text = date_text.get('$', '')

    result = PublicationData(
            catalog='scopus',
            catalog_identifier=id,
            href=_get_scopus_publication_link(a.data.get('coredata')),
            doi=a.data.get('coredata', {}).get('prism:doi', ''),
            title=a.data.get('coredata', {}).get('dc:title', ''),
            journal_name=a.data.get('coredata', {}).get('prism:publicationName', ''),
            publication_cover_date=a.data.get('coredata', {}).get('prism:coverDate', ''),
            abstract_text=a.data.get('coredata', {}).get('dc:description', ''),
            funding_text=a.funding_text,
            funding_list=a.funding_list,
            volume=a.data.get('coredata', {}).get('prism:volume', ''),
            issue=a.data.get('coredata', {}).get('prism:issueIdentifier', ''),
            pages=a.data.get('coredata', {}).get('prism:pageRange', ''),
            subtype_code=a.data.get('coredata', {}).get('subtype', ''),
            subtype_description=a.data.get('coredata', {}).get('subtypeDescription', ''),
            cited_by_count=convert_int_nullable(a.data.get('coredata', {}).get(u'citedby-count')),
            authors=a.authors,
            keywords=list(filter(None, set([k.get('$', '') for k in (a.data.get(u'authkeywords') or {}).get('author-keywords', [])]))),
            is_open_access=a.data.get('coredata', {}).get(u'openaccess', '0') == "1",
            raw_text=json.dumps(a.data, sort_keys=True, indent=4),
            action='get_scopus_publication_data',
            publication_year=publication_date.get('year', None),
            publication_month=publication_date.get('month', None),
            publication_day=publication_date.get('day', None),
            publication_date_text=date_text,       
        )
    
    return result


def get_scopus_publications(identifier):
    logging.debug('started')

    if not current_app.config['SCOPUS_ENABLED']:
        logging.warn('SCOPUS Not Enabled')
        return []
    
    search_results = DocumentSearch(identifier)
    search_results.execute(_client(), get_all=True)

    result = []

    for p in search_results.results:
        id = p.get(u'dc:identifier', ':').split(':')[1]

        if not id:
            # SCOPUS sends an "Empty Set" result as opposed to no results
            continue

        result.append(
            PublicationData(
                catalog='scopus',
                catalog_identifier=id,
                href=_get_scopus_publication_link(p),
                doi=p.get(u'prism:doi', ''),
                title=p.get(u'dc:title', ''),
                journal_name=p.get(u'prism:publicationName', ''),
                publication_cover_date=parse_date(p.get(u'prism:coverDate', '')),
                abstract_text=p.get(u'dc:description', ''),
                funding_text='',
                funding_list=[],
                volume=p.get(u'prism:volume', ''),
                issue=p.get(u'prism:issueIdentifier', ''),
                pages=p.get(u'prism:pageRange', ''),
                subtype_code=p.get(u'subtype', ''),
                subtype_description=p.get(u'subtypeDescription', ''),
                cited_by_count=int(p.get(u'citedby-count', '0')),
                authors=[_translate_publication_author(a, 'get_scopus_publications') for a in p.get('author', [])],
                keywords=set(p.get(u'authkeywords', '').split('|')),
                is_open_access=p.get(u'openaccess', '0') == "1",
                raw_text=json.dumps(p, sort_keys=True, indent=4),
                action='get_scopus_publications',
            ))

    return result


def _translate_publication_author(author_dict, action):

    afils = ensure_list(author_dict.get('afid'))

    affiliations = [
        AffiliationData(
            catalog=CATALOG_SCOPUS,
            catalog_identifier=a.get('$'),
            raw_text=json.dumps(a, sort_keys=True, indent=4),
            action=action,
        ) for a in afils if a.get('$')
    ]

    result = AuthorData(
        catalog=CATALOG_SCOPUS,
        catalog_identifier=author_dict.get('authid', None),
        orcid=author_dict.get('orcid', None),
        first_name=author_dict.get('given-name', None),
        last_name=author_dict.get('surname', None),
        initials=author_dict.get('initials', None),
        author_name=author_dict.get('authname', None),
        href=author_dict.get('author-url', None),
        affiliations=affiliations,
        raw_text=json.dumps(author_dict, sort_keys=True, indent=4),
        action=action,
    )

    return result


def get_scopus_author_data(identifier):
    logging.debug(f'Getting Scopus Author Data {identifier}')

    if not current_app.config['SCOPUS_ENABLED']:
        logging.warn('SCOPUS Not Enabled')
        return None

    result = Author(identifier)

    if not result.populate(_client()):
        return None
    
    return result.get_data()


def get_scopus_affiliation_data(identifier):
    logging.debug(f'Getting Scopus Affiliation Data {identifier}')

    if not current_app.config['SCOPUS_ENABLED']:
        logging.warn('SCOPUS Not Enabled')
        return None

    result = ScopusAffiliation(identifier)
    result.read(_client())

    return result.get_data()


def scopus_similar_authors(academic: Academic):
    return scopus_author_search(academic.last_name)


def scopus_author_search(search_string, search_non_local=False):

    if not current_app.config['SCOPUS_ENABLED']:
        logging.warn('SCOPUS Not Enabled')
        print('B')
        return _test_author_search_data()

    re_orcid = re.compile(r'\d{4}-\d{4}-\d{4}-\d{4}$')

    if re_orcid.match(search_string):
        q = f'ORCID({search_string})'
    elif search_string.isnumeric():
        q = f'AU-ID({search_string})'
    else:
        q = ' AND '.join({f'(AUTHLASTNAME({w}) OR AUTHFIRST({w}))' for w in search_string.split()})
        # q = f'AUTHLASTNAME({search_string})'

    if search_non_local:
        auth_srch = ElsSearch(f'{q}','author')
    else:
        auth_srch = ElsSearch(f'{q} AND (affil(leicester) OR affil(loughborough) OR affil(northampton))','author')

    auth_srch.execute(_client(), get_all=True)

    existing_catalog_identifiers = set(db.session.execute(
        select(Source.catalog_identifier)
        .where(Source.academic_id != None)
        .where(Source.catalog == CATALOG_SCOPUS)
    ).scalars())

    result = []

    for r in auth_srch.results:
        href = ''
        for h in r.get(u'coredata', {}).get(u'link', ''):
            if h['@rel'] == 'scopus-author':
                href = h['@href']

        afils = ensure_list(r.get('affiliation-current'))

        affiliations = [
            AffiliationData(
                catalog=CATALOG_SCOPUS,
                catalog_identifier=a.get('affiliation-id'),
                name=a.get('affiliation-name'),
                address=a.get('affiliation-city'),
                country=a.get('affiliation-country'),
                raw_text=json.dumps(a, sort_keys=True, indent=4),
                action='scopus_author_search',
            ) for a in afils if a.get('affiliation-id')
        ]

        a = AuthorData(
            catalog=CATALOG_SCOPUS,
            catalog_identifier=r.get(u'dc:identifier', ':').split(':')[1],
            orcid=r.get(u'coredata', {}).get(u'orcid', ''),
            first_name=r.get(u'preferred-name', {}).get(u'given-name', ''),
            last_name=r.get(u'preferred-name', {}).get(u'surname', ''),
            initials=r.get(u'preferred-name', {}).get('initials', None),
            href=href,
            affiliations=affiliations,
            raw_text=json.dumps(r, sort_keys=True, indent=4),
            action='scopus_author_search',
        )

        if len(a.catalog_identifier) == 0:
            continue

        a.existing = a.catalog_identifier in existing_catalog_identifiers

        result.append(a)

    return result


def _test_author_search_data():
    result = []
    for _ in range(randint(1,20)):
        a = AuthorData(
            catalog=CATALOG_SCOPUS,
            catalog_identifier='powkf',
            orcid='frerferf',
            first_name='Richard',
            last_name='Bramley',
            initials='RA',
            href='',
            affiliations=[],
        )
        a.existing=choice([True, False])
        result.append(a)
        
    return result


class Author(ElsAuthor):
    def __init__(self, catalog_identifier):
        self.catalog_identifier = catalog_identifier
        self.orcid = None
        self.href = None
        self.initials = None
        self.citation_count = None
        self.document_count = None
        self.h_index = None

        super().__init__(author_id=self.catalog_identifier)

    @property
    def first_name(self):
        if self.data:
            return self.data.get(u'author-profile', {}).get('preferred-name', {}).get('given-name', '')
        else:
            return ''

    @property
    def last_name(self):
        if self.data:
            return self.data.get(u'author-profile', {}).get('preferred-name', {}).get('surname', '')
        else:
            return ''

    def _set_orcid(self):
        self.orcid = self.data.get(u'coredata', {}).get(u'orcid', '')

    def _set_href(self):
        for h in  self.data.get(u'coredata', {}).get(u'link', ''):
            if h['@rel'] == 'scopus-author':
                self.href = h['@href']

    def _set_initials(self):
        self.initials = self.data.get(u'author-profile', {}).get(u'preferred-name', {}).get(u'initials', '')

    def _set_citation_count(self):
        self.citation_count = self.data.get(u'coredata', {}).get(u'citation-count', '')

    def _set_document_count(self):
        self.document_count = self.data.get(u'coredata', {}).get(u'document-count', '')

    def _set_h_index(self):
        self.h_index = self.data.get(u'h-index', None)

    def populate(self, client):
        result = self.read(client)
        self.read_metrics(client)

        return result

    def read(self, client):
        try:
            result = super().read(client)
        except ResourceNotFoundException as e:
            return False
        except Exception as e:
            log_exception(e)
            logging.error('Error reading Scopus data')
            raise e
        
        if self.data is None:
            logging.error('No error reading Scopus data, but data is still None')
            raise Exception('No error reading Scopus data, but data is still None')

        self._set_initials()
        self._set_citation_count()
        self._set_document_count()
        self._set_h_index()

        return result

    def read_metrics(self, client):
        try:
            fields = [
                    "document-count",
                    "cited-by-count",
                    "citation-count",
                    "h-index",
                    "dc:identifier",
                    ]
            api_response = client.exec_request(self.uri + "?field=" + ",".join(fields))
            data = api_response[self._payload_type][0]
            if not self.data:
                self._data = dict()
                self._data['coredata'] = dict()
            if data.get('coredata', {}).get('citation-count', None):
                self.citation_count = data['coredata']['citation-count']
            if data.get('coredata', {}).get('document-count', None):
                self.document_count = data['coredata']['document-count']
            if data.get('h-index', None):
                self.h_index = data['h-index']
            logging.debug('Added/updated author metrics')
        except ResourceNotFoundException as e:
            return False
        except Exception as e:
            log_exception(e)
            logging.debug('Error reading Scopus metrics')
            return None
        
        if self.data is None:
            logging.debug('No error reading Scopus metrics, but data is still None')
            return False

        return True

    def get_data(self):
        afils = ensure_list(self.data.get('affiliation-current'))

        affiliations = [
            AffiliationData(
                catalog=CATALOG_SCOPUS,
                catalog_identifier=a.get('@id'),
                name=a.get('@name'),
                address=a.get('@city'),
                country=a.get('@country'),
                raw_text=json.dumps(a, sort_keys=True, indent=4),
                action='get_data',
            ) for a in afils if a.get('@id')
        ]

        result = AuthorData(
            catalog=CATALOG_SCOPUS,
            catalog_identifier=self.catalog_identifier,
            orcid=self.orcid,
            first_name=self.first_name,
            last_name=self.last_name,
            initials=self.initials,
            href=self.href,
            citation_count=self.citation_count,
            document_count=self.document_count,
            h_index=self.h_index,
            affiliations=affiliations,
            raw_text=json.dumps(self.data, sort_keys=True, indent=4),
            action='get_data',
        )

        return result


class ScopusAffiliation(ElsAffil):
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

    def get_data(self):
        return AffiliationData(
            catalog=CATALOG_SCOPUS,
            catalog_identifier=self.affiliation_id,
            name=self.name,
            address=self.address,
            country=self.country,
            raw_text=json.dumps(self.data, sort_keys=True, indent=4),
            action='get_data',
        )


class Abstract(AbsDoc):
    def __init__(self, scopus_id=None, doi=None):
        self.scopus_id = scopus_id
        self.doi = doi

        if self.doi:
            super().__init__(uri=f'https://api.elsevier.com/content/abstract/doi/{doi}')
        else:
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

    @property
    def abstract_text(self):
        if not self.data:
            return ''

        funding_text = self.data.get('item', {}).get('xocs:meta', {}).get('xocs:funding-list', {}).get('xocs:funding-text', '')

        if type(funding_text) is list:
            return '\n'.join([t.get('$', '') for t in funding_text])
        else:
            return funding_text

    @property
    def authors(self):
        return [self._translate_publication_author(a, 'authors') for a in ((self.data or {}).get('authors') or {}).get('author', [])]


    def _translate_publication_author(self, author_dict, action):

        afils = ensure_list(self.data.get('affiliation'))

        affiliations = [AffiliationData(
            catalog=CATALOG_SCOPUS,
            catalog_identifier=a.get('@id') or '',
            raw_text=a.get('@id') or '',
            action=action,
        ) for a in afils if a.get('@id')]

        result = AuthorData(
            catalog=CATALOG_SCOPUS,
            catalog_identifier=author_dict.get('@auid', None),
            orcid='',
            first_name=author_dict.get('ce:given-name', None),
            last_name=author_dict.get('ce:surname', None),
            initials=author_dict.get('ce:initials', None),
            author_name=author_dict.get('ce:indexed-name', None),
            href=author_dict.get('author-url', None),
            affiliations=affiliations,
            raw_text=json.dumps(author_dict, sort_keys=True, indent=4),
            action=action,
        )

        return result

    def read(self, client):
        try:
            return super().read(client)
        except Exception as e:
            logging.error(e)
            return False


class DocumentSearch(ElsSearch):
    def __init__(self, identifier):
        q = f'au-id({identifier})'

        if not current_app.config['LOAD_OLD_PUBLICATIONS']:
            q = f'{q} AND PUBYEAR > {current_app.config["HISTORIC_PUBLICATION_CUTOFF"].year - 1}'

        super().__init__(query=q, index='scopus')
        self._uri += '&view=complete'
