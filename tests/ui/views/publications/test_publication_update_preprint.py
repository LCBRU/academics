from functools import cache
import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester, FlaskViewTester


class PublicationUpdatePreprintViewBaseTester(FlaskViewTester):
    @property
    def endpoint(self):
        return 'ui.publication_update_preprint'
    
    @cache
    def user_to_login(self, faker):
        return faker.user().validator(save=True)

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.publication = faker.publication().get(save=True)
        self.catalog_publication = faker.catalog_publication().get(save=True, publication=self.publication)
        self.parameters['id'] = self.publication.id
        self.parameters['is_preprint'] = 1


class TestPublicationUpdat6ePreprintRequiresLogin(PublicationUpdatePreprintViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestPublicationUpdatePreprintGet(PublicationUpdatePreprintViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__post(self):
        resp = self.post()

    # Todo: Add more tests for not found, permissions, etc.