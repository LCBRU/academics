import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class PublicationJournalOptionsViewTester:
    @property
    def endpoint(self):
        return 'ui.publication_journal_options'


class TestPublicationJournalOptionsRequiresLogin(PublicationJournalOptionsViewTester, RequiresLoginTester):
    ...


class TestPublicationJournalOptionsGet(PublicationJournalOptionsViewTester, FlaskViewLoggedInTester):
    def user_to_login(self, faker):
        return faker.user().admin(save=True)

    @pytest.mark.app_crsf(True)
    def test__get(self):
        resp = self.get()        

    # Todo: Add more tests for invalid data, etc.
