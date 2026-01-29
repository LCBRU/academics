import pytest
from lbrc_flask.pytest.testers import IndexTester, RequiresLoginTester, PagedSize20ResultSet, PanelListContentAsserter, RowContentAsserter


class JournalIndexTester:
    @property
    def endpoint(self):
        return 'ui.journals'


class JournalRowContentAsserter(PanelListContentAsserter):
    def assert_row_details(self, row, expected_result):
        assert row is not None
        assert expected_result is not None

    # Todo: Add specific assertions for journal row details


class TestJournalIndexRequiresLogin(JournalIndexTester, RequiresLoginTester):
    ...


class TestJournalIndex(JournalIndexTester, IndexTester):
    @property
    def content_asserter(self) -> RowContentAsserter:
        return JournalRowContentAsserter

    @pytest.mark.parametrize("item_count", PagedSize20ResultSet.test_page_edges())
    @pytest.mark.parametrize("current_page", PagedSize20ResultSet.test_current_pages())
    def test__get__no_filters(self, item_count, current_page):
        journals = self.faker.journal().get_list(
            save=True,
            item_count=item_count,
        )

        self.parameters['page'] = current_page

        resp = self.get()

        self.assert_all(
            page_count_helper=PagedSize20ResultSet(page=current_page, expected_results=journals),
            resp=resp,
        )

    # Todo: Add more tests for filtering, sorting, etc.
