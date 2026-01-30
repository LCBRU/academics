import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class PublicationAuthorsViewTester:
    @property
    def endpoint(self):
        return 'ui.publication_authors'
    
    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.publication = faker.publication().get(save=True)
        self.catalog_publications = faker.catalog_publication().get(save=True, publication=self.publication)
        self.parameters['id'] = self.publication.id
        self.parameters['author_selector'] = 'bob'


class TestPublicationAuthorsRequiresLogin(PublicationAuthorsViewTester, RequiresLoginTester):
    ...


class TestPublicationAuthorsGet(PublicationAuthorsViewTester, FlaskViewLoggedInTester):
    def user_to_login(self, faker):
        return faker.user().admin(save=True)

    @pytest.mark.app_crsf(True)
    def test__get(self):
        resp = self.get()        

    # Todo: Add more tests for invalid data, etc.
