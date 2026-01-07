import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from lbrc_flask.pytest.form_tester import FormTester, FormTesterSearchField, FormTesterCheckboxField
from tests.ui.views.academics import AcademicViewTester


class AddAuthorSubmitViewBaseTester(AcademicViewTester):
    @property
    def endpoint(self):
        return 'ui.add_author_submit'


class TestAddAuthorSubmitRequiresLogin(AddAuthorSubmitViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post
    

class AddAuthorSubmitViewTester(AddAuthorSubmitViewBaseTester):
    @pytest.fixture(autouse=True)
    def set_editor_user(self, editor_user):
        pass


class TestAddAuthorSubmitPost(AddAuthorSubmitViewTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.post()

        # To do: Add tests for submitting stuff here
