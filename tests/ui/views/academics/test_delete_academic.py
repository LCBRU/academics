import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from lbrc_flask.pytest.form_tester import FormTester, FormTesterSearchField, FormTesterCheckboxField
from tests.ui.views.academics import AcademicViewTester


class DeleteAcademicViewBaseTester(AcademicViewTester):
    @property
    def endpoint(self):
        return 'ui.delete_academic'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.existing = faker.academic().get_in_db()
        self.parameters['id'] = self.existing.id


class TestDeleteAcademicRequiresLogin(DeleteAcademicViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post
    

class DeleteAcademicViewTester(DeleteAcademicViewBaseTester):
    @pytest.fixture(autouse=True)
    def set_editor_user(self, editor_user):
        pass


class TestDeleteAcademicPost(DeleteAcademicViewTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.post()

        # To do: Add tests for deleting stuff here
