import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class FolderAddPublicationViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.folder_add_publication'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.folder = faker.folder().get(save=True)
        self.parameters['folder_id'] = self.folder.id


class TestFolderAddPublicationRequiresLogin(FolderAddPublicationViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestFolderAddPublicationGet(FolderAddPublicationViewBaseTester, FlaskViewLoggedInTester):
    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker, login_fixture):
        self.folder = faker.folder().get(save=True, owner_id=self.loggedin_user.id)
        self.parameters['folder_id'] = self.folder.id

    @pytest.mark.app_crsf(True)
    def test__post(self):
        publication = self.faker.publication().get(save=True)
        data = {
            'id': publication.id,
        }
        resp = self.post(data=data)

    # Todo: Add more tests for not found, permissions, checking shared users, etc.