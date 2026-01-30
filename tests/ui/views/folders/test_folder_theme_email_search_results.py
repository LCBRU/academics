import pytest
from lbrc_flask.pytest.testers import IndexTester, RequiresLoginTester


class FolderThemeEmailSearchResultsTester:
    @property
    def endpoint(self):
        return 'ui.folder_theme_email_search_results'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.theme = faker.theme().get(save=True)
        self.folder = faker.folder().get(save=True, owner_id=self.user_to_login(faker).id)
        self.parameters['folder_id'] = self.folder.id
        self.parameters['theme_id'] = self.theme.id


class TestFolderThemeEmailSearchResultsRequiresLogin(FolderThemeEmailSearchResultsTester, RequiresLoginTester):
    ...


class TestFolderThemeEmailSearchResults(FolderThemeEmailSearchResultsTester, IndexTester):
    def test__post(self):
        resp = self.get()

        # Todd: Add tests check content
