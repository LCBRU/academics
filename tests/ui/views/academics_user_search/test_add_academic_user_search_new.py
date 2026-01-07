import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from tests.ui.views.users import UserEditFormTester


class AcademicUserSearchNewViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.academic_user_search_new'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.existing = faker.academic().get_in_db()
        self.parameters['academic_id'] = self.existing.id


class TestAcademicUserSearchNewRequiresLogin(AcademicUserSearchNewViewBaseTester, RequiresLoginTester):
    ...


class AcademicUserSearchNewViewTester(AcademicUserSearchNewViewBaseTester):
    @pytest.fixture(autouse=True)
    def set_editor_user(self, editor_user):
        pass


class TestAcademicUserNewSearchGet(AcademicUserSearchNewViewTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.get()

        UserEditFormTester(has_csrf=False).assert_all(resp)
