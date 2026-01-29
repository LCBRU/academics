import pytest
from lbrc_flask.pytest.testers import IndexTester, RequiresLoginTester


class GroupAcademicSearchResultsTester:
    @property
    def endpoint(self):
        return 'ui.group_acadmic_search_results'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.group = faker.group().get(save=True)
        self.parameters['group_id'] = self.group.id


class TestGroupAcademicSearchResultsRequiresLogin(GroupAcademicSearchResultsTester, RequiresLoginTester):
    ...


class TestGroupAcademicSearchResults(GroupAcademicSearchResultsTester, IndexTester):
    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker, login_fixture):
        self.group = faker.group().get(save=True, owner_id=self.loggedin_user.id)
        self.parameters['group_id'] = self.group.id

    def test__post(self):
        resp = self.get()

        # Todd: Add tests check content
