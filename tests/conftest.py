import pytest
from faker import Faker
from lbrc_flask.pytest.fixtures import *
from lbrc_flask.pytest.faker import LbrcFlaskFakerProvider
from lbrc_flask.pytest.helpers import login
from academics import create_app
from academics.config import TestConfig
from academics.security import init_authorization
from tests.faker import AcademicProvider, UserProvider


@pytest.fixture(scope="function")
def loggedin_user(client, faker):
    init_authorization()
    return login(client, faker)


@pytest.fixture(scope="function")
def app(tmp_path):
    class LocalTestConfig(TestConfig):
        FILE_UPLOAD_DIRECTORY = tmp_path

    yield create_app(LocalTestConfig)


@pytest.fixture(scope="function")
def faker():
    result: Faker = Faker("en_GB")
    result.add_provider(UserProvider)
    result.add_provider(LbrcFlaskFakerProvider)
    result.add_provider(AcademicProvider)

    yield result
