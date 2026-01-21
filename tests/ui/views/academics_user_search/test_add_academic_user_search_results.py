import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class AcademicUserSearchResultsViewTester:
    @property
    def endpoint(self):
        return 'ui.academic_user_search_results'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.existing = faker.academic().get(save=True)
        self.parameters['academic_id'] = self.existing.id


class TestAcademicUserSearchResultsRequiresLogin(AcademicUserSearchResultsViewTester, RequiresLoginTester):
    ...


class TestAcademicUserSearchResultsGet(AcademicUserSearchResultsViewTester, FlaskViewLoggedInTester):
    def user_to_login(self, faker):
        return faker.user().editor()

    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.get()

        # To do: Add results tests here