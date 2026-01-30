import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class PublicationAuthorOptionsViewTester:
    @property
    def endpoint(self):
        return 'ui.publication_author_options'


class TestPublicationAuthorOptionsRequiresLogin(PublicationAuthorOptionsViewTester, RequiresLoginTester):
    ...


class TestPublicationAuthorOptionsGet(PublicationAuthorOptionsViewTester, FlaskViewLoggedInTester):
    def user_to_login(self, faker):
        return faker.user().admin(save=True)

    @pytest.mark.app_crsf(True)
    def test__get(self):
        resp = self.get()        

    # Todo: Add more tests for invalid data, etc.
