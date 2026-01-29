import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class GroupDeleteViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.group_delete'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.group = faker.group().get(save=True)
        self.parameters['id'] = self.group.id


class TestGroupDeleteRequiresLogin(GroupDeleteViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestGroupDeleteGet(GroupDeleteViewBaseTester, FlaskViewLoggedInTester):
    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker, login_fixture):
        self.group = faker.group().get(save=True, owner_id=self.loggedin_user.id)
        self.parameters['id'] = self.group.id

    @pytest.mark.app_crsf(True)
    def test__post(self):
        resp = self.post()

        assert self.faker.group().get_by_id(self.group.id) is None

    # Todo: Add more tests for not found, permissions, etc.