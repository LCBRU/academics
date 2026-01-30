from functools import cache
import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester, FlaskViewTester


class CatalogPublicationDeleteViewBaseTester(FlaskViewTester):
    @property
    def endpoint(self):
        return 'ui.catalog_publication_delete'
    
    @cache
    def user_to_login(self, faker):
        return faker.user().editor(save=True)

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.catalog_publication = faker.catalog_publication().get(save=True)
        self.parameters['id'] = self.catalog_publication.id


class TestCatalogPublicationDeleteRequiresLogin(CatalogPublicationDeleteViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestCatalogPublicationDeletePost(CatalogPublicationDeleteViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__post(self):
        resp = self.post()

    # Todo: Add more tests for not found, permissions, etc.