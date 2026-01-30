import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class PublicationKeywordOptionsViewTester:
    @property
    def endpoint(self):
        return 'ui.publication_keyword_options'


class TestPublicationKeywordOptionsRequiresLogin(PublicationKeywordOptionsViewTester, RequiresLoginTester):
    ...


class TestPublicationKaywordOptionsGet(PublicationKeywordOptionsViewTester, FlaskViewLoggedInTester):
    def user_to_login(self, faker):
        return faker.user().admin(save=True)

    @pytest.mark.app_crsf(True)
    def test__get(self):
        resp = self.get()        

    # Todo: Add more tests for invalid data, etc.
