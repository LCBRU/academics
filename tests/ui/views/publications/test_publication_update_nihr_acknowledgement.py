from functools import cache
import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester, FlaskViewTester


class PublicationUpdateNihrAcknowledgementViewBaseTester(FlaskViewTester):
    @property
    def endpoint(self):
        return 'ui.publication_update_nihr_acknowledgement'
    
    @cache
    def user_to_login(self, faker):
        return faker.user().validator(save=True)

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.publication = faker.publication().get(save=True)
        self.catalog_publication = faker.catalog_publication().get(save=True, publication=self.publication)
        self.parameters['id'] = self.publication.id
        self.parameters['nihr_acknowledgement_id'] = faker.nihr_acknowledgement().choice_from_db().id


class TestPublicationUpdateNihrAcknowledgementRequiresLogin(PublicationUpdateNihrAcknowledgementViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestPublicationUpdateNiheAcknowledgementGet(PublicationUpdateNihrAcknowledgementViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__post(self):
        resp = self.post()

    # Todo: Add more tests for not found, permissions, etc.