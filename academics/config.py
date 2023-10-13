import os
from lbrc_flask.config import BaseConfig, BaseTestConfig
from lbrc_flask.validators import parse_date


class Config(BaseConfig):
    SCOPUS_API_KEY = os.environ["SCOPUS_API_KEY"]
    SCOPUS_ENABLED = os.environ.get("SCOPUS_ENABLED", 'True').lower() == 'true'
    OPEN_ALEX_EMAIL = os.environ["OPEN_ALEX_EMAIL"]
    OPEN_ALEX_ENABLED = os.environ.get("OPEN_ALEX_ENABLED", 'True').lower() == 'true'
    HISTORIC_PUBLICATION_CUTOFF = parse_date(os.environ["HISTORIC_PUBLICATION_CUTOFF"])
    LOAD_OLD_PUBLICATIONS = os.environ.get("LOAD_OLD_PUBLICATIONS", 'False').lower() == 'true'


class TestConfig(BaseTestConfig):
    pass
