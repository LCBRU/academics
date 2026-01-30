from functools import cache
import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester, FlaskViewTester


class PublicationDeleteSupplementaryAuthorViewBaseTester(FlaskViewTester):
    @property
    def endpoint(self):
        return 'ui.publication_delete_supplementary_author'
    
    @cache
    def user_to_login(self, faker):
        return faker.user().editor(save=True)

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.supplementary_author = faker.academic().get(save=True)
        self.publication = faker.publication().get(save=True, supplementary_authors=[self.supplementary_author])
        self.catalog_publication = faker.catalog_publication().get(save=True, publication=self.publication)
        self.parameters['id'] = self.publication.id
        self.parameters['academic_id'] = self.supplementary_author.id


class TestPublicationDeleteSupplementaryAuthorRequiresLogin(PublicationDeleteSupplementaryAuthorViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestPublicationDeletePublicationAuthorPost(PublicationDeleteSupplementaryAuthorViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__post(self):
        resp = self.post()

    # Todo: Add more tests for not found, permissions, etc.