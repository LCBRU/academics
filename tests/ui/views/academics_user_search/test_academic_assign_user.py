import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from tests.ui.views.academics import AcademicViewTester


class AcademicAssignUserViewBaseTester(AcademicViewTester):
    @property
    def endpoint(self):
        return 'ui.academic_assign_user'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.existing = faker.academic().get_in_db()
        self.parameters['academic_id'] = self.existing.id

        self.user = faker.user().get_in_db()
        self.parameters['id'] = self.user.id


class TestAcademicAssignUserRequiresLogin(AcademicAssignUserViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post
    

class AcademicAssignUserViewTester(AcademicAssignUserViewBaseTester):
    @pytest.fixture(autouse=True)
    def set_editor_user(self, editor_user):
        pass


class TestAcademicAssignUserPost(AcademicAssignUserViewTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.post()

        # To do: Add tests for assigning users to academics here
