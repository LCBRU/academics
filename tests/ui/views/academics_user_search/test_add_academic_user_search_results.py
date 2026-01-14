import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester

from academics.security import ROLE_EDITOR


class AcademicUserSearchResultsViewTester:
    @property
    def endpoint(self):
        return 'ui.academic_user_search_results'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.existing = faker.academic().get_in_db()
        self.parameters['academic_id'] = self.existing.id


class TestAcademicUserSearchResultsRequiresLogin(AcademicUserSearchResultsViewTester, RequiresLoginTester):
    ...


class TestAcademicUserSearchResultsGet(AcademicUserSearchResultsViewTester, FlaskViewLoggedInTester):
    def user_to_login(self, faker):
        return faker.user().get_in_db(rolename=ROLE_EDITOR)

    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.get()

        # To do: Add results tests here