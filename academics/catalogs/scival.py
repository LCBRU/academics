from datetime import datetime
import logging
import requests
import time
import json
from flask import current_app
from functools import cache
from cachetools import cached, TTLCache
from academics.catalogs.data_classes import InstitutionData

from academics.model.catalog import CATALOG_SCIVAL


class ResourceNotFoundException(Exception):
    pass


class SciValClient:
    __min_req_interval = 1
    __ts_last_req = time.time()

    def __init__(self, api_key) -> None:
        self._api_key = api_key

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
        r = requests.get(URL, params=dict(apiKey=self._api_key))

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


def get_scival_publication_institutions(scopus_id=None, log_data=False):
    logging.debug('started')

    if not current_app.config['SCIVAL_ENABLED']:
        logging.warn('SCIVAL Not Enabled')
        return []

    try:
        result = _client().exec_request(f'https://api.elsevier.com/analytics/scival/publication/{scopus_id}')
        logging.info(f'Scival IS found for {scopus_id}')

        if log_data:
            logging.info(result)
            with open('rich_dump.json', 'w') as f:
                f.write(json.dumps(result))

        return [InstitutionData(
            catalog=CATALOG_SCIVAL,
            catalog_identifier=i.get('id'),
            name=i.get('name'),
            country_code=i.get('countryCode'),
            sector=None,
            action="get_scival_publication_institutions",
        ) for i in result.get('publication', {}).get('institutions')]

    except Exception as e:
        logging.warn(f'Scival NOT found for {scopus_id}')

        return []


def get_scival_institution(institution_id=None):
    logging.debug('started')

    if not current_app.config['SCIVAL_ENABLED']:
        logging.warn('SCIVAL Not Enabled')
        return []

    try:
        result = _client().exec_request(f'https://api.elsevier.com/analytics/scival/institution/{institution_id}')
        logging.info(f'Institution IS found for {institution_id}')

        i = result.get('institution')

        if not i:
            return None

        return InstitutionData(
            catalog=CATALOG_SCIVAL,
            catalog_identifier=i.get('id'),
            name=i.get('name'),
            country_code=i.get('countryCode'),
            sector=i.get('sector'),
            action="get_scival_institution",
        )

    except Exception as e:
        logging.warn(f'Institution NOT found for {institution_id}')

        return None
