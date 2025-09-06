import pytest
from faker import Faker
from lbrc_flask.pytest.fixtures import *
from lbrc_flask.pytest.faker import LbrcFlaskFakerProvider
from lbrc_flask.pytest.helpers import login
from lbrc_flask.security import add_user_to_role
from academics import create_app
from academics.config import TestConfig
from academics.security import init_authorization
from tests.faker import AcademicProvider, UserProvider
from academics.security import ROLE_EDITOR


@pytest.fixture(scope="function", autouse=True)
def authorization_setup(client, faker):
    init_authorization()


@pytest.fixture(scope="function")
def loggedin_user(client, faker):
    return login(client, faker)


@pytest.fixture(scope="function")
def editor_user(loggedin_user):
    add_user_to_role(loggedin_user, ROLE_EDITOR)
    return loggedin_user


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
