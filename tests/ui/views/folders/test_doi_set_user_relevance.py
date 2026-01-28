import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class FolderDoiSetUserRelevanceViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.folder_doi_set_user_relevance'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.folder_doi = faker.folder_doi().get(save=True)
        self.parameters['folder_id'] = self.folder_doi.folder.id
        self.parameters['doi'] = self.folder_doi.doi
        self.parameters['relevant'] = 0


class TestFolderDoiSetUserRelevanceRequiresLogin(FolderDoiSetUserRelevanceViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestFolderDoiSetUserRelevanceGet(FolderDoiSetUserRelevanceViewBaseTester, FlaskViewLoggedInTester):
    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker, login_fixture):
        folder = faker.folder().get(save=True, owner=self.loggedin_user)
        self.folder_doi = faker.folder_doi().get(save=True, folder=folder)
        self.parameters['folder_id'] = self.folder_doi.folder.id
        self.parameters['doi'] = self.folder_doi.doi
        self.parameters['relevant'] = 0

    @pytest.mark.app_crsf(True)
    def test__post(self):
        resp = self.post()
