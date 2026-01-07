import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from lbrc_flask.pytest.form_tester import FormTester, FormTesterSearchField, FormTesterCheckboxField
from tests.ui.views.academics import AcademicViewTester


class AddAuthorSearchResultsViewBaseTester(AcademicViewTester):
    @property
    def endpoint(self):
        return 'ui.add_author_search_results'


class TestAddAuthorSearchResultsRequiresLogin(AddAuthorSearchResultsViewBaseTester, RequiresLoginTester):
    ...


class AddAuthorSearchResultsViewTester(AddAuthorSearchResultsViewBaseTester):
    @pytest.fixture(autouse=True)
    def set_editor_user(self, editor_user):
        pass


class TestAddAuthorSearchGet(AddAuthorSearchResultsViewTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.get()

        # To do: Test the results returned
