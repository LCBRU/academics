from datetime import date, datetime
import logging
import requests
import time
import re
import json
from elsapy.elssearch import ElsSearch
from elsapy.elsprofile import ElsAuthor, ElsAffil
from academics.catalogs.data_classes import AffiliationData, AuthorData, PublicationData
from elsapy.elsdoc import AbsDoc
from elsapy.elsclient import ElsClient
from flask import current_app, jsonify
from sqlalchemy import select
from lbrc_flask.database import db
from lbrc_flask.logging import log_exception
from lbrc_flask.validators import parse_date
from lbrc_flask.data_conversions import ensure_list
from elsapy import version
from functools import cache
from cachetools import cached, TTLCache
from academics.model.academic import Academic, Source

from academics.model.catalog import CATALOG_SCOPUS


class ResourceNotFoundException(Exception):
    pass


class SciValClient:
    __min_req_interval = 1
    __ts_last_req = time.time()

    def __init__(self, api_key) -> None:
        self.headers = {
            "X-ELS-APIKey"  : api_key,
            "Accept"        : 'application/json'
        }        

    def _throttle(self):
        interval = time.time() - self.__ts_last_req

        logging.debug(f'Checking throttle - Time: {time.time()}; Last Request: {self.__ts_last_req}; Interval: {interval}')
        if (interval < self.__min_req_interval):
            logging.debug(f'Throttle Start: {time.time()}')
            time.sleep( self.__min_req_interval - interval )
            logging.debug(f'Throttle End: {time.time()}')

        self.__ts_last_req = time.time()
        

    @cached(cache=TTLCache(maxsize=1024, ttl=60*60))
    def exec_request(self, URL):
        self._throttle()

        logging.info('Sending GET request to ' + URL)
        r = requests.get(URL, headers=self.headers)

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
            raise requests.HTTPError(f"HTTP {str(r.status_code)} Error from {URL} using headers {str(self.headers)}:\n{r.text}")
        elif r.status_code == 404:
            raise ResourceNotFoundException(f'Resource not found: for URL {URL}')
        else:
            raise requests.HTTPError(f"HTTP {str(r.status_code)} Error from {URL} using headers {str(self.headers)}:\n{r.text}")


@cache
def _client():
    return SciValClient(current_app.config['SCOPUS_API_KEY'])


def get_scival_publication_data(scopus_id=None):
    logging.debug('started')

    if not current_app.config['SCIVAL_ENABLED']:
        logging.warn('SCIVAL Not Enabled')
        return []

    result = _client().exec_request(f'https://api.elsevier.com/analytics/scival/publication/{scopus_id}')

    logging.info(result)
