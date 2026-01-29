import pytest
from lbrc_flask.pytest.testers import IndexTester, RequiresLoginTester, PagedResultSet, TableContentAsserter, RowContentAsserter


class GroupIndexTester:
    @property
    def endpoint(self):
        return 'ui.groups'


class GroupRowContentAsserter(TableContentAsserter):
    def assert_row_details(self, row, expected_result):
        assert row is not None
        assert expected_result is not None

        # Todo: Add specific assertions for group row details


class TestGroupIndexRequiresLogin(GroupIndexTester, RequiresLoginTester):
    ...


class TestGroupIndex(GroupIndexTester, IndexTester):
    @property
    def content_asserter(self) -> RowContentAsserter:
        return GroupRowContentAsserter

    @pytest.mark.parametrize("item_count", PagedResultSet.test_page_edges())
    @pytest.mark.parametrize("current_page", PagedResultSet.test_current_pages())
    def test__get__no_filters(self, item_count, current_page):
        groups = self.faker.group().get_list(
            save=True,
            item_count=item_count,
            owner=self.loggedin_user,
        )

        self.parameters['page'] = current_page

        resp = self.get()

        self.assert_all(
            page_count_helper=PagedResultSet(page=current_page, expected_results=groups),
            resp=resp,
        )

    # Todo: Add more tests for filtering, sorting, etc.
