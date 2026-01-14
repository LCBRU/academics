import pytest
from faker import Faker
from lbrc_flask.pytest.fixtures import *
from lbrc_flask.pytest.faker import LbrcFlaskFakerProvider
from academics import create_app
from academics.config import TestConfig
from academics.security import init_authorization
from tests.faker import AcademicsProvider


@pytest.fixture(scope="function", autouse=True)
def authorization_setup(client, faker):
    init_authorization()


@pytest.fixture(scope="function")
def app(tmp_path):
    class LocalTestConfig(TestConfig):
        FILE_UPLOAD_DIRECTORY = tmp_path

    yield create_app(LocalTestConfig)


@pytest.fixture(scope="function")
def faker():
    result: Faker = Faker("en_GB")
    result.add_provider(LbrcFlaskFakerProvider)
    result.add_provider(AcademicsProvider)

    yield result
