import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class GroupRemoveShareduserViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.group_remove_shared_user'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.shared_user = faker.user().get(save=True)
        self.group = faker.group().get(
            save=True,
            shared_users=[self.shared_user],
        )

        self.parameters['id'] = self.group.id
        self.parameters['user_id'] = self.shared_user.id


class TestGroupRemoveSharedUserRequiresLogin(GroupRemoveShareduserViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestGroupRemoveSharedUserGet(GroupRemoveShareduserViewBaseTester, FlaskViewLoggedInTester):
    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker, login_fixture):
        self.shared_user = faker.user().get(save=True)
        self.group = faker.group().get(
            save=True,
            shared_users=[self.shared_user],
            owner_id=self.loggedin_user.id,
        )

        self.parameters['id'] = self.group.id
        self.parameters['user_id'] = self.shared_user.id

    @pytest.mark.app_crsf(True)
    def test__post(self):
        resp = self.post()

    # Todo: Add more tests for not found, permissions, checking shared users, etc.
