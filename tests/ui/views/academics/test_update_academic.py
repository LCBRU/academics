from unittest.mock import patch
import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from tests.ui.views.academics import AcademicViewTester


class UpdateAcademicViewBaseTester(AcademicViewTester):
    @property
    def endpoint(self):
        return 'ui.update_academic'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.existing = faker.academic().get_in_db()
        self.parameters['id'] = self.existing.id


class TestUpdateAcademicRequiresLogin(UpdateAcademicViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post
    

class UpdateAcademicViewTester(UpdateAcademicViewBaseTester):
    @pytest.fixture(autouse=True)
    def set_editor_user(self, editor_user):
        pass


class TestUpdateAcademicPost(UpdateAcademicViewTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    @patch('academics.ui.views.academics.run_jobs_asynch') # Mocking as cereal tasks do not work in testing
    def test__get__has_form(self, run_jobs_asynch):
        resp = self.post()

        # To do: Add tests for updating stuff here
