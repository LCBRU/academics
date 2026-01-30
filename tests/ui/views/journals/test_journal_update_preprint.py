import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class JournalUpdatePreprintViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.journal_update_preprint'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.journal = faker.journal().get(save=True, owner_id=self.user_to_login(faker).id)
        self.parameters['id'] = self.journal.id
        self.parameters['is_preprint'] = 1


class TestJournalUpdatePreprintRequiresLogin(JournalUpdatePreprintViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestJournalUpdatePreprintGet(JournalUpdatePreprintViewBaseTester, FlaskViewLoggedInTester):
    def user_to_login(self, faker):
        return faker.user().validator(save=True)
    
    @pytest.mark.app_crsf(True)
    def test__post(self):
        resp = self.post()

        assert self.faker.journal().get_by_id(self.journal.id) is not None

    # Todo: Add more tests for not found, permissions, etc.