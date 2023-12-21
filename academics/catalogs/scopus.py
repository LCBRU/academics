from collections.abc import Mapping
from datetime import date, datetime
import logging
import requests
import time
import re
import json
from elsapy.elssearch import ElsSearch
from elsapy.elsprofile import ElsAuthor, ElsAffil
from academics.catalogs.utils import AffiliationData, AuthorData, PublicationData
from academics.model import CATALOG_SCOPUS, Academic, Source
from elsapy.elsdoc import AbsDoc
from elsapy.elsclient import ElsClient
from flask import current_app
from sqlalchemy import select
from lbrc_flask.database import db
from lbrc_flask.logging import log_exception
from lbrc_flask.validators import parse_date
from elsapy import version
from functools import cache
from cachetools import cached, TTLCache


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
            raise requests.HTTPError("HTTP " + str(r.status_code) + " Error from " + URL + "\nand using headers " + str(headers) + ":\n" + r.text)


@cache
def _client():
    return ScopusClient(current_app.config['SCOPUS_API_KEY'])


def _get_scopus_publication_link(p):
    for h in p.get(u'link', ''):
        if h.get('@rel', '') == 'scopus' or h.get('@ref', '') == 'scopus':
            return h['@href']


def get_scopus_publication_data(identifier):
    logging.debug('get_scopus_publication_data: started')

    if not current_app.config['SCOPUS_ENABLED']:
        logging.warn('SCOPUS Not Enabled')
        return []
    
    a = Abstract(identifier)
    a.read(_client())

    id = a.data.get('coredata', {}).get(u'dc:identifier', ':').split(':')[1]

    return PublicationData(
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
            cited_by_count=int(a.data.get('coredata', {}).get(u'citedby-count', '0')),
            authors=a.authors,
            keywords=list(filter(None, set([k.get('$', '') for k in (a.data.get(u'authkeywords') or {}).get('author-keywords', [])]))),
            is_open_access=a.data.get('coredata', {}).get(u'openaccess', '0') == "1",
            affiliations=a.affiliations,
        )


def get_scopus_publications(identifier):
    logging.debug('get_scopus_publications: started')

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

        logging.getLogger('query').warn(json.dumps(p))

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
                authors=[_translate_publication_author(a) for a in p.get('author', [])],
                keywords=set(p.get(u'authkeywords', '').split('|')),
                is_open_access=p.get(u'openaccess', '0') == "1",
                affiliations=_translate_publication_affiliations(p),
            ))

    

    return result


def _translate_publication_affiliations(publication_dict):
    result = []

    afils = publication_dict.get('affiliation') or []

    if isinstance(afils, Mapping):
        afils = [afils]

    for a in afils or []:
        result.append(
            AffiliationData(
                catalog=CATALOG_SCOPUS,
                catalog_identifier=a.get('afid') or '',
                name=a.get('affilname') or '',
                address=a.get('affiliation-city') or '',
                country=a.get('affiliation-country') or '',
            )
        )
    
    return result


def _translate_publication_author(author_dict):

    afils = author_dict.get('afid') or []

    if isinstance(afils, Mapping):
        afils = [afils]

    affiliations = [
        AffiliationData(
            catalog=CATALOG_SCOPUS,
            catalog_identifier=a.get('$'),
        ) for a in afils if a.get('$')
    ]

    logging.getLogger('query').warn(affiliations)

    result = AuthorData(
        catalog=CATALOG_SCOPUS,
        catalog_identifier=author_dict.get('authid', None),
        orcid=author_dict.get('orcid', None),
        first_name=author_dict.get('given-name', None),
        last_name=author_dict.get('surname', None),
        initials=author_dict.get('initials', None),
        author_name=author_dict.get('authname', None),
        href=author_dict.get('author-url', None),
        affiliation_identifier='',
        affiliation_name='',
        affiliation_address='',
        affiliation_country='',
        affiliations=affiliations,
    )

    return result


def get_scopus_author_data(identifier, get_extended_details=False):
    logging.debug(f'Getting Scopus Author Data {identifier}')

    if not current_app.config['SCOPUS_ENABLED']:
        logging.warn('SCOPUS Not Enabled')
        return None

    result = Author(identifier)

    if not result.populate(_client(), get_extended_details):
        return None

    return result.get_data()


def scopus_similar_authors(academic: Academic):
    return scopus_author_search(academic.last_name)


def scopus_author_search(search_string):
    if not current_app.config['SCOPUS_ENABLED']:
        logging.warn('SCOPUS Not Enabled')
        return []

    re_orcid = re.compile(r'\d{4}-\d{4}-\d{4}-\d{4}$')

    if re_orcid.match(search_string):
        q = f'ORCID({search_string})'
    else:
        q = f'authlast({search_string})'

    auth_srch = ElsSearch(f'{q} AND affil(leicester)','author')
    auth_srch.execute(_client())

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

        logging.getLogger('query').warn(json.dumps(r))

        affiliation_identifier = r.get(u'affiliation-current', {}).get(u'affiliation-id', '')

        sa = ScopusAffiliation(affiliation_identifier)
        sa.read(_client())

        a = AuthorData(
            catalog=CATALOG_SCOPUS,
            catalog_identifier=r.get(u'dc:identifier', ':').split(':')[1],
            orcid=r.get(u'coredata', {}).get(u'orcid', ''),
            first_name=r.get(u'preferred-name', {}).get(u'given-name', ''),
            last_name=r.get(u'preferred-name', {}).get(u'surname', ''),
            initials=r.get(u'preferred-name', {}).get('initials', None),
            href=href,
            affiliation_identifier=affiliation_identifier,
            affiliation_name=sa.name,
            affiliation_address=sa.address,
            affiliation_country=sa.country,
            affiliations=[],
        )

        if len(a.catalog_identifier) == 0:
            continue

        a.existing = a.catalog_identifier in existing_catalog_identifiers

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
        self.affiliation_id = None
        self.affiliation_name = None
        self.affiliation_address = None
        self.affiliation_country = None

        super().__init__(author_id=self.catalog_identifier)

    def _set_orcid(self):
        self.orcid = self.data.get(u'coredata', {}).get(u'orcid', '')

    def _set_href(self):
        for h in  self.data.get(u'coredata', {}).get(u'link', ''):
            if h['@rel'] == 'scopus-author':
                self.href = h['@href']

    def _set_initials(self):
        self.initials = self.data.get(u'author-profile', {}).get(u'preferred-name').get(u'initials', '')

    def _set_citation_count(self):
        self.citation_count = self.data.get(u'coredata', {}).get(u'citation-count', '')

    def _set_document_count(self):
        self.document_count = self.data.get(u'coredata', {}).get(u'document-count', '')

    def _set_h_index(self):
        self.h_index = self.data.get(u'h-index', None)

    def _set_affiliation_id(self):
        self.affiliation_id = self.data.get(u'affiliation-current', {}).get(u'@id', '')

    def _set_affiliation_name(self):
        self.affiliation_name = self.data.get(u'affiliation-current', {}).get(u'@name', '')

    def _set_affiliation_address(self):
        self.affiliation_address = self.data.get(u'affiliation-current', {}).get(u'@city', '')

    def _set_affiliation_country(self):
        self.affiliation_country = self.data.get(u'affiliation-current', {}).get(u'@country', '')

    def populate(self, client, get_extended_details):
        result = self.read(client)

        if get_extended_details:
            self.read_metrics(client)

            if self.affiliation_id:
                sa = ScopusAffiliation(self.affiliation_id)
                sa.read(client)

                self.affiliation_name = sa.name
                self.affiliation_address = sa.address
                self.affiliation_country = sa.country
        
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
        self._set_affiliation_id()
        self._set_affiliation_name()
        self._set_affiliation_address()
        self._set_affiliation_country()

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
        result = AuthorData(
            catalog=CATALOG_SCOPUS,
            catalog_identifier=self.catalog_identifier,
            orcid=self.orcid,
            first_name=self.first_name,
            last_name=self.last_name,
            initials=self.initials,
            href=self.href,
            affiliation_identifier=self.affiliation_id,
            affiliation_name=None,
            affiliation_address=None,
            affiliation_country=None,
            citation_count=self.citation_count,
            document_count=self.document_count,
            h_index=self.h_index,
            affiliations=[],
        )

        # HERERERERERE



        if self.affiliation_id:
            sa = ScopusAffiliation(self.affiliation_id)
            sa.read(_client())

            result.affiliation_name=sa.name,
            result.affiliation_address=sa.address
            result.affiliation_country=sa.country
        else:
            logging.warn('No error affiliation ID')

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
        return [self._translate_publication_author(a) for a in self.data.get('authors', {}).get('author', [])]


    @property
    def affiliations(self):
        result = []

        afils = self.data.get('affiliation') or []

        if isinstance(afils, Mapping):
            afils = [afils]

        for a in afils:
            result.append(
                AffiliationData(
                    catalog=CATALOG_SCOPUS,
                    catalog_identifier=a.get('@id') or '',
                    name=a.get('affilname') or '',
                    address=a.get('affiliation-city') or '',
                    country=a.get('affiliation-country') or '',
                )
            )
        
        return result


    def _translate_publication_author(self, author_dict):

        afils = self.data.get('affiliation') or []

        if isinstance(afils, Mapping):
            afils = [afils]

        affiliations = [AffiliationData(
            catalog=CATALOG_SCOPUS,
            catalog_identifier=a.get('@id') or '',
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
            affiliation_identifier='',
            affiliation_name='',
            affiliation_address='',
            affiliation_country='',
            affiliations=affiliations,
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
            q = f'{q} AND PUBYEAR > {date.today().year - 1}'

        super().__init__(query=q, index='scopus')
        self._uri += '&view=complete'

