import pytest
from lbrc_flask.pytest.testers import IndexTester, RequiresLoginTester, PagedResultSet, PanelListContentAsserter, RowContentAsserter


class AcademicPotentialSourcesIndexTester:
    @property
    def endpoint(self):
        return 'ui.academics_potential_sources'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.existing = faker.academic().get(save=True)
        self.parameters['id'] = self.existing.id


class TestAcademicPotentialSourcesRequiresLogin(AcademicPotentialSourcesIndexTester, RequiresLoginTester):
    ...


class TestAcademicsPotentialSourcesIndex(AcademicPotentialSourcesIndexTester, IndexTester):
    def test__get(self):
        resp = self.get()

    # Todo: Add more tests for filtering, sorting, etc.
