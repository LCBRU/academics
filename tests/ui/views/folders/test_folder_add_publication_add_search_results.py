import pytest
from lbrc_flask.pytest.testers import IndexTester, RequiresLoginTester


class FolderAddPublicationAddSearchResultsTester:
    @property
    def endpoint(self):
        return 'ui.folder_add_publication_add_search_results'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.folder = faker.folder().get(save=True, owner_id=self.user_to_login(faker).id)
        self.parameters['folder_id'] = self.folder.id


class TestFolderAddPublicationAddSearchResultsRequiresLogin(FolderAddPublicationAddSearchResultsTester, RequiresLoginTester):
    ...


class TestFolderAddPublicationAddSearchResults(FolderAddPublicationAddSearchResultsTester, IndexTester):
    def test__post(self):
        resp = self.get()

        # Todd: Add tests check content
