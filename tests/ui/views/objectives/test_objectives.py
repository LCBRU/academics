import pytest
from lbrc_flask.pytest.testers import IndexTester, RequiresLoginTester, PagedResultSet, PanelListContentAsserter, RowContentAsserter


class ObjectivesIndexTester:
    @property
    def endpoint(self):
        return 'ui.objectives'


class ObjectivesRowContentAsserter(PanelListContentAsserter):
    def assert_row_details(self, row, expected_result):
        assert row is not None
        assert expected_result is not None

    # Todo: Add specific assertions for journal row details


class TestObjectivesRequiresLogin(ObjectivesIndexTester, RequiresLoginTester):
    ...


class TestObjectivesIndex(ObjectivesIndexTester, IndexTester):
    @property
    def content_asserter(self) -> RowContentAsserter:
        return ObjectivesRowContentAsserter

    @pytest.mark.parametrize("item_count", PagedResultSet.test_page_edges())
    @pytest.mark.parametrize("current_page", PagedResultSet.test_current_pages())
    def test__get__no_filters(self, item_count, current_page):
        theme = self.faker.theme().get(save=True)
        objectives = self.faker.objective().get_list(
            save=True,
            item_count=item_count,
            theme_id=theme.id,
        )

        self.parameters['theme_id'] = theme.id
        self.parameters['page'] = current_page

        resp = self.get()

        self.assert_all(
            page_count_helper=PagedResultSet(page=current_page, expected_results=objectives),
            resp=resp,
        )

    # Todo: Add more tests for filtering, sorting, etc.
