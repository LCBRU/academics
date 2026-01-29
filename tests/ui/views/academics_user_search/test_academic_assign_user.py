import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from tests.ui.views.academics import AcademicViewTester


class AcademicAssignUserViewTester(AcademicViewTester):
    @property
    def endpoint(self):
        return 'ui.academic_assign_user'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.existing = faker.academic().get(save=True)
        self.parameters['academic_id'] = self.existing.id

        self.user = faker.user().get(save=True)
        self.parameters['id'] = self.user.id


class TestAcademicAssignUserRequiresLogin(AcademicAssignUserViewTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post
    

class TestAcademicAssignUserPost(AcademicAssignUserViewTester, FlaskViewLoggedInTester):
    def user_to_login(self, faker):
        return faker.user().editor(save=True)

    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.post()

        # To do: Add tests for assigning users to academics here
