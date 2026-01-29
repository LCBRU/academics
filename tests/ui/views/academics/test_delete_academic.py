import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from tests.ui.views.academics import AcademicViewTester


class DeleteAcademicViewTester(AcademicViewTester):
    @property
    def endpoint(self):
        return 'ui.delete_academic'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.existing = faker.academic().get(save=True)
        self.parameters['id'] = self.existing.id


class TestDeleteAcademicRequiresLogin(DeleteAcademicViewTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post
    

class TestDeleteAcademicPost(DeleteAcademicViewTester, FlaskViewLoggedInTester):
    def user_to_login(self, faker):
        return faker.user().editor(save=True)

    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.post()

        # To do: Add tests for deleting stuff here
