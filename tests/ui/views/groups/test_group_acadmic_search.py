import pytest
from lbrc_flask.pytest.testers import IndexTester, RequiresLoginTester


class GroupAddAcadmicSearchTester:
    @property
    def endpoint(self):
        return 'ui.group_acadmic_search'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.group = faker.group().get(save=True, owner_id=self.user_to_login(faker).id)
        self.parameters['group_id'] = self.group.id


class TestGroupAddAcadmicSearchRequiresLogin(GroupAddAcadmicSearchTester, RequiresLoginTester):
    ...


class TestGroupAddAcadmicSearch(GroupAddAcadmicSearchTester, IndexTester):
    def test__post(self):
        resp = self.get()

        # Todd: Add tests check content
