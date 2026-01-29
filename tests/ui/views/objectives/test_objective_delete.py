import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class ObjectiveDeleteViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.objective_delete'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.objective = faker.objective().get(save=True)
        self.parameters['id'] = self.objective.id


class TestObjectiveDeleteRequiresLogin(ObjectiveDeleteViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestObjectiveDeleteGet(ObjectiveDeleteViewBaseTester, FlaskViewLoggedInTester):
    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker, login_fixture):
        self.objective = faker.objective().get(save=True, owner_id=self.loggedin_user.id)
        self.parameters['id'] = self.objective.id
    
    @pytest.mark.app_crsf(True)
    def test__post(self):
        resp = self.post()

        assert self.faker.objective().get_by_id(self.objective.id) is None

    # Todo: Add more tests for not found, permissions, etc.