from unittest.mock import patch
import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class FolderEmailYourselfViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.folder_email_yourself'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.folder = faker.folder().get(save=True, owner_id=self.user_to_login(faker).id)
        self.theme = faker.theme().get(save=True)
        self.parameters['folder_id'] = self.folder.id
        self.parameters['theme_id'] = self.theme.id


class TestFolderEmailYourselfRequiresLogin(FolderEmailYourselfViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestFolderEmailYourselfPost(FolderEmailYourselfViewBaseTester, FlaskViewLoggedInTester):
    @patch('academics.ui.views.folders.email_theme_folder_publication_list') # Mocking as cereal tasks do not work in testing
    @pytest.mark.app_crsf(True, )
    def test__post(self, email_theme_folder_publication_list):
        resp = self.post()

    # Todo: Add more tests for not found, permissions, etc.