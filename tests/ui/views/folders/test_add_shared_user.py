import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class FolderAddShareduserViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.folder_add_shared_user'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.folder = faker.folder().get(save=True, owner_id=self.user_to_login(faker).id)
        self.parameters['folder_id'] = self.folder.id


class TestFolderAddSharedUserRequiresLogin(FolderAddShareduserViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestFolderAddSharedUserGet(FolderAddShareduserViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__post(self):
        user = self.faker.user().get(save=True)
        data = {
            'id': user.id,
        }
        resp = self.post(data=data)

    # Todo: Add more tests for not found, permissions, checking shared users, etc.