import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from tests.ui.views.academics import AcademicViewTester


class AddAcademicSubmitViewTester(AcademicViewTester):
    @property
    def endpoint(self):
        return 'ui.add_author_submit'


class TestAddAcademicSubmitRequiresLogin(AddAcademicSubmitViewTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post
    

class TestAddAcademicSubmitPost(AddAcademicSubmitViewTester, FlaskViewLoggedInTester):
    def user_to_login(self, faker):
        return faker.user().editor(save=True)

    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.post()

        # To do: Add tests for submitting stuff here
