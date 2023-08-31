import os
from lbrc_flask.config import BaseConfig, BaseTestConfig


class Config(BaseConfig):
    SCOPUS_API_KEY = os.environ["SCOPUS_API_KEY"]
    OPEN_ALEX_EMAIL = os.environ["OPEN_ALEX_EMAIL"]
    HISTORIC_PUBLICATION_CUTOFF = os.environ["HISTORIC_PUBLICATION_CUTOFF"]


class TestConfig(BaseTestConfig):
    pass
