import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester, FlaskViewTester


class PublicationAddFolderViewBaseTester(FlaskViewTester):
    @property
    def endpoint(self):
        return 'ui.publication_add_folder'
    
    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.folder = faker.folder().get(save=True)
        self.publication = faker.publication().get(save=True)
        self.catalog_publication = faker.catalog_publication().get(save=True, publication=self.publication)
        self.parameters['publication_id'] = self.publication.id


class TestPublicationFolderAuthorRequiresLogin(PublicationAddFolderViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestPublicationAddFolderPost(PublicationAddFolderViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__post(self):
        data = {'id': self.folder.id}
        resp = self.post(data)

    # Todo: Add more tests for not found, permissions, etc.