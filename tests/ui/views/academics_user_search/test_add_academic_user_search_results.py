import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class AcademicUserSearchResultsViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.academic_user_search_results'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.existing = faker.academic().get_in_db()
        self.parameters['academic_id'] = self.existing.id


class TestAcademicUserSearchResultsRequiresLogin(AcademicUserSearchResultsViewBaseTester, RequiresLoginTester):
    ...


class AcademicUserSearchResultsViewTester(AcademicUserSearchResultsViewBaseTester):
    @pytest.fixture(autouse=True)
    def set_editor_user(self, editor_user):
        pass


class TestAcademicUserSearchResultsGet(AcademicUserSearchResultsViewTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.get()

        # To do: Add results tests here