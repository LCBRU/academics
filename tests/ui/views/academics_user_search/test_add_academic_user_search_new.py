import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from tests.ui.views.users import UserEditFormTester


class AcademicUserSearchNewViewTester:
    @property
    def endpoint(self):
        return 'ui.academic_user_search_new'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.existing = faker.academic().get_in_db()
        self.parameters['academic_id'] = self.existing.id


class TestAcademicUserSearchNewRequiresLogin(AcademicUserSearchNewViewTester, RequiresLoginTester):
    ...


class TestAcademicUserNewSearchGet(AcademicUserSearchNewViewTester, FlaskViewLoggedInTester):
    def user_to_login(self, faker):
        return faker.user().editor()

    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.get()

        UserEditFormTester(has_csrf=False).assert_all(resp)
