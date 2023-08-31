import os
from lbrc_flask.config import BaseConfig, BaseTestConfig
from lbrc_flask.validators import parse_date


class Config(BaseConfig):
    SCOPUS_API_KEY = os.environ["SCOPUS_API_KEY"]
    OPEN_ALEX_EMAIL = os.environ["OPEN_ALEX_EMAIL"]
    HISTORIC_PUBLICATION_CUTOFF = parse_date(os.environ["HISTORIC_PUBLICATION_CUTOFF"])


class TestConfig(BaseTestConfig):
    pass
