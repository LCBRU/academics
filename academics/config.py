import os
from lbrc_flask.config import BaseConfig, BaseTestConfig
from lbrc_flask.validators import parse_date


class SharedConfig:
    HISTORIC_PUBLICATION_CUTOFF = parse_date(os.environ["HISTORIC_PUBLICATION_CUTOFF"])

class Config(BaseConfig, SharedConfig):
    SCOPUS_API_KEY = os.environ["SCOPUS_API_KEY"]
    SCOPUS_ENABLED = os.environ.get("SCOPUS_ENABLED", 'True').lower() == 'true'
    SCIVAL_ENABLED = os.environ.get("SCIVAL_ENABLED", 'True').lower() == 'true'
    WORKER_STOPS_ON_ERROR = os.environ.get("WORKER_STOPS_ON_ERROR", 'False').lower() == 'true'
    OPEN_ALEX_EMAIL = os.environ["OPEN_ALEX_EMAIL"]
    OPEN_ALEX_ENABLED = os.environ.get("OPEN_ALEX_ENABLED", 'True').lower() == 'true'
    LOAD_OLD_PUBLICATIONS = os.environ.get("LOAD_OLD_PUBLICATIONS", 'False').lower() == 'true'


class TestConfig(BaseTestConfig, SharedConfig):
    ...