import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class FolderDeleteViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.folder_delete'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.folder = faker.folder().get(save=True)
        self.parameters['id'] = self.folder.id


class TestFolderDeleteRequiresLogin(FolderDeleteViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestFolderDeleteGet(FolderDeleteViewBaseTester, FlaskViewLoggedInTester):
    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker, login_fixture):
        self.folder = faker.folder().get(save=True, owner_id=self.loggedin_user.id)
        self.parameters['id'] = self.folder.id

    @pytest.mark.app_crsf(True)
    def test__post(self):
        resp = self.post()

        assert self.faker.folder().get_by_id(self.folder.id) is None

    # Todo: Add more tests for not found, permissions, etc.