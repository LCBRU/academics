import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class GroupAddAcademicViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.group_add_academic'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.group = faker.group().get(save=True, owner_id=self.user_to_login(faker).id)
        self.parameters['group_id'] = self.group.id


class TestGroupAddAcademicRequiresLogin(GroupAddAcademicViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestGroupAddAcademicGet(GroupAddAcademicViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__post(self):
        academic = self.faker.academic().get(save=True)
        data = {
            'id': academic.id,
        }
        resp = self.post(data=data)

    # Todo: Add more tests for not found, permissions, checking shared users, etc.