import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from tests.ui.views.academics import AcademicViewTester


class AddAcademicSearchResultsViewTester(AcademicViewTester):
    @property
    def endpoint(self):
        return 'ui.add_author_search_results'


class TestAddAcademicSearchResultsRequiresLogin(AddAcademicSearchResultsViewTester, RequiresLoginTester):
    ...


class TestAddAcademicSearchGet(AddAcademicSearchResultsViewTester, FlaskViewLoggedInTester):
    def user_to_login(self, faker):
        return faker.user().editor(save=True)

    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.get()

        # To do: Test the results returned
