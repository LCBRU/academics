import os
from lbrc_flask.config import BaseConfig, BaseTestConfig


class Config(BaseConfig):
    SCOPUS_API_KEY = os.environ["SCOPUS_API_KEY"]
    HISTORIC_PUBLICATION_CUTOFF = os.environ["HISTORIC_PUBLICATION_CUTOFF"]


class TestConfig(BaseTestConfig):
    pass
