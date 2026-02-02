from functools import cache
from unittest.mock import patch
import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class AcademicsAmendPotentialSourcesViewTester:
    @property
    def endpoint(self):
        return 'ui.academics_amend_potential_sources'
    
    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.academic = faker.academic().get(save=True)
        self.academic_potential_source = faker.academic_potential_source().get(
            save=True,
            academic_id=self.academic.id,
        )
        self.parameters['id'] = self.academic_potential_source.id
        self.parameters['academic_id'] = self.academic.id
        self.parameters['status'] = 'match'

    @cache
    def user_to_login(self, faker):
        return faker.user().editor(save=True)


class TestAcademicsAmendPotentialSourcesRequiresLogin(AcademicsAmendPotentialSourcesViewTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestAcademicsAmendPotentialSourcesPost(AcademicsAmendPotentialSourcesViewTester, FlaskViewLoggedInTester):
    @patch('academics.ui.views.sources.run_jobs_asynch') # Mocking as cereal tasks do not work in testing
    @pytest.mark.app_crsf(True)
    def test__post(self, run_jobs_asynch):
        resp = self.post()        

    # Todo: Add more tests for invalid data, etc.
