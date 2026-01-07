import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from tests.ui.views.academics import AcademicViewTester


class AddAcademicSubmitViewBaseTester(AcademicViewTester):
    @property
    def endpoint(self):
        return 'ui.add_author_submit'


class TestAddAcademicSubmitRequiresLogin(AddAcademicSubmitViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post
    

class AddAcademicSubmitViewTester(AddAcademicSubmitViewBaseTester):
    @pytest.fixture(autouse=True)
    def set_editor_user(self, editor_user):
        pass


class TestAddAcademicSubmitPost(AddAcademicSubmitViewTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.post()

        # To do: Add tests for submitting stuff here
