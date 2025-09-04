import pytest
from lbrc_flask.pytest.testers import IndexTester, RequiresLoginGetTester, PanelListRowResultsTester


class AcademicIndexTester:
    @property
    def endpoint(self):
        return 'ui.index'


class TestAcademicIndex(AcademicIndexTester, IndexTester):
    @property
    def row_results_tester(self):
        return PanelListRowResultsTester()

    @pytest.mark.parametrize("item_count", IndexTester.page_edges())
    def test__get__no_filters(self, item_count):
        self.faker.academic().get_list_in_db(item_count=item_count)
        self.get_and_assert_standards(expected_count=item_count)


class TestSiteIndexRequiresLogin(AcademicIndexTester, RequiresLoginGetTester):
    ...
