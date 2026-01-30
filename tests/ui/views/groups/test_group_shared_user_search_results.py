import pytest
from lbrc_flask.pytest.testers import IndexTester, RequiresLoginTester


class GroupSharedUserSearchResultsTester:
    @property
    def endpoint(self):
        return 'ui.group_shared_user_search_results'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.group = faker.group().get(save=True, owner_id=self.user_to_login(faker).id)
        self.parameters['group_id'] = self.group.id


class TestGroupSharedUserSearchResultsRequiresLogin(GroupSharedUserSearchResultsTester, RequiresLoginTester):
    ...


class TestGroupSharedUserSearchResults(GroupSharedUserSearchResultsTester, IndexTester):
    def test__post(self):
        resp = self.get()

        # Todd: Add tests check content
