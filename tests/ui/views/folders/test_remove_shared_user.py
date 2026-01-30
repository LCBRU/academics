import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class FolderRemoveShareduserViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.folder_remove_shared_user'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.shared_user = faker.user().get(save=True)
        self.folder = faker.folder().get(
            save=True,
            shared_users=[self.shared_user],
            owner_id=self.user_to_login(faker).id,
        )

        self.parameters['id'] = self.folder.id
        self.parameters['user_id'] = self.shared_user.id


class TestFolderAddSharedUserRequiresLogin(FolderRemoveShareduserViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestFolderAddSharedUserGet(FolderRemoveShareduserViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__post(self):
        resp = self.post()

    # Todo: Add more tests for not found, permissions, checking shared users, etc.