from unittest.mock import patch
import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from academics.security import ROLE_EDITOR
from tests.ui.views.academics import AcademicViewTester


class UpdateAcademicViewTester(AcademicViewTester):
    @property
    def endpoint(self):
        return 'ui.update_academic'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.existing = faker.academic().get_in_db()
        self.parameters['id'] = self.existing.id


class TestUpdateAcademicRequiresLogin(UpdateAcademicViewTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post
    

class TestUpdateAcademicPost(UpdateAcademicViewTester, FlaskViewLoggedInTester):
    def user_to_login(self, faker):
        return faker.user().get_in_db(rolename=ROLE_EDITOR)

    @pytest.mark.app_crsf(True)
    @patch('academics.ui.views.academics.run_jobs_asynch') # Mocking as cereal tasks do not work in testing
    def test__get__has_form(self, run_jobs_asynch):
        resp = self.post()

        # To do: Add tests for updating stuff here
