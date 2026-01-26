import pytest
from lbrc_flask.pytest.testers import IndexTester, RequiresLoginTester, PagedResultSet, TableContentAsserter, RowContentAsserter


class FolderIndexTester:
    @property
    def endpoint(self):
        return 'ui.folders'


class FolderRowContentAsserter(TableContentAsserter):
    def assert_row_details(self, row, expected_result):
        assert row is not None
        assert expected_result is not None

        # Todo: Add specific assertions for folder row details


class TestFolderIndexRequiresLogin(FolderIndexTester, RequiresLoginTester):
    ...


class TestFolderIndex(FolderIndexTester, IndexTester):
    @property
    def content_asserter(self) -> RowContentAsserter:
        return FolderRowContentAsserter

    @pytest.mark.parametrize("item_count", PagedResultSet.test_page_edges())
    @pytest.mark.parametrize("current_page", PagedResultSet.test_current_pages())
    def test__get__no_filters(self, item_count, current_page):
        folders = self.faker.folder().get_list(
            save=True,
            item_count=item_count,
            owner=self.loggedin_user,
        )

        self.parameters['page'] = current_page

        resp = self.get()

        self.assert_all(
            page_count_helper=PagedResultSet(page=current_page, expected_results=folders),
            resp=resp,
        )

    # Todo: Add more tests for filtering, sorting, etc.
