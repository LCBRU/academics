import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from tests.ui.views.academics import AcademicViewTester


class AddAcademicSearchResultsViewBaseTester(AcademicViewTester):
    @property
    def endpoint(self):
        return 'ui.add_author_search_results'


class TestAddAcademicSearchResultsRequiresLogin(AddAcademicSearchResultsViewBaseTester, RequiresLoginTester):
    ...


class AddAcademicSearchResultsViewTester(AddAcademicSearchResultsViewBaseTester):
    @pytest.fixture(autouse=True)
    def set_editor_user(self, editor_user):
        pass


class TestAddAcademicSearchGet(AddAcademicSearchResultsViewTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.get()

        # To do: Test the results returned
