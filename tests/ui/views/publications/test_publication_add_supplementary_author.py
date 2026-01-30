from functools import cache
import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester, FlaskViewTester


class PublicationAddSupplementaryAuthorViewBaseTester(FlaskViewTester):
    @property
    def endpoint(self):
        return 'ui.publication_add_supplementary_author'
    
    @cache
    def user_to_login(self, faker):
        return faker.user().editor(save=True)

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.supplementary_author = faker.academic().get(save=True)
        self.publication = faker.publication().get(save=True)
        self.catalog_publication = faker.catalog_publication().get(save=True, publication=self.publication)
        self.parameters['publication_id'] = self.publication.id


class TestPublicationAddSupplementaryAuthorRequiresLogin(PublicationAddSupplementaryAuthorViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestPublicationAddPublicationAuthorPost(PublicationAddSupplementaryAuthorViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__post(self):
        data = {'id': self.supplementary_author.id}
        resp = self.post(data)

    # Todo: Add more tests for not found, permissions, etc.