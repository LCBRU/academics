import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from academics.security import ROLE_EDITOR
from tests.ui.views.academics import AcademicViewTester


class AddAcademicSearchResultsViewTester(AcademicViewTester):
    @property
    def endpoint(self):
        return 'ui.add_author_search_results'


class TestAddAcademicSearchResultsRequiresLogin(AddAcademicSearchResultsViewTester, RequiresLoginTester):
    ...


class TestAddAcademicSearchGet(AddAcademicSearchResultsViewTester, FlaskViewLoggedInTester):
    def user_to_login(self, faker):
        return faker.user().get_in_db(rolename=ROLE_EDITOR)

    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.get()

        # To do: Test the results returned
