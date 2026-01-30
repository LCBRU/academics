import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class GroupAddShareduserViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.group_add_shared_user'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.group = faker.group().get(save=True, owner_id=self.user_to_login(faker).id)
        self.parameters['group_id'] = self.group.id


class TestGroupAddSharedUserRequiresLogin(GroupAddShareduserViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestGroupAddSharedUserGet(GroupAddShareduserViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__post(self):
        user = self.faker.user().get(save=True)
        data = {
            'id': user.id,
        }
        resp = self.post(data=data)

    # Todo: Add more tests for not found, permissions, checking shared users, etc.