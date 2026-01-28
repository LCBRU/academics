import pytest
from lbrc_flask.pytest.testers import IndexTester, RequiresLoginTester


class FolderAddPublicationAddSearchTester:
    @property
    def endpoint(self):
        return 'ui.folder_add_publication_add_search'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.folder = faker.folder().get(save=True)
        self.parameters['folder_id'] = self.folder.id


class TestFolderAddPublicationAddSearchRequiresLogin(FolderAddPublicationAddSearchTester, RequiresLoginTester):
    ...


class TestFolderAddPublicationAddSearch(FolderAddPublicationAddSearchTester, IndexTester):
    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker, login_fixture):
        self.folder = faker.folder().get(save=True, owner_id=self.loggedin_user.id)
        self.parameters['folder_id'] = self.folder.id

    def test__post(self):
        resp = self.get()

        # Todd: Add tests check content
