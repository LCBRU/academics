from functools import cache
import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class DeleteSourceViewTester:
    @property
    def endpoint(self):
        return 'ui.delete_source'
    
    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.source = faker.source().get(save=True)
        self.parameters['id'] = self.source.id

    @cache
    def user_to_login(self, faker):
        return faker.user().editor(save=True)


class TestDeleteRequiresLogin(DeleteSourceViewTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestDeleteSourcePost(DeleteSourceViewTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__post(self):
        resp = self.post()        

    # Todo: Add more tests for invalid data, etc.
