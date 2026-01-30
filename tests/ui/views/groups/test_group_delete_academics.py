import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class GroupDeleteAcademicViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.group_delete_acadmic'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.academic = faker.academic().get(save=True)
        self.group = faker.group().get(
            save=True,
            academics=[self.academic],
            owner_id=self.user_to_login(faker).id,
        )

        self.parameters['group_id'] = self.group.id
        self.parameters['academic_id'] = self.academic.id


class TestGroupDeleteAcademicRequiresLogin(GroupDeleteAcademicViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestGroupDeleteAcademicGet(GroupDeleteAcademicViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__post(self):
        resp = self.post()

    # Todo: Add more tests for not found, permissions, checking shared users, etc.
