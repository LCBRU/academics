from unittest.mock import patch
import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class RefreshInstitutionsViewTester:
    @property
    def endpoint(self):
        return 'ui.refresh_institutions'


class TestRefreshInstitutionsRequiresLogin(RefreshInstitutionsViewTester, RequiresLoginTester):
    ...


class TestRefreshInstitutionsGet(RefreshInstitutionsViewTester, FlaskViewLoggedInTester):
    def user_to_login(self, faker):
        return faker.user().admin(save=True)

    @patch('academics.ui.views.jobs.run_jobs_asynch') # Mocking as cereal tasks do not work in testing
    @pytest.mark.app_crsf(True)
    def test__get__has_form(self, run_jobs_asynch):
        resp = self.get()        

    # Todo: Add more tests for invalid data, etc.
