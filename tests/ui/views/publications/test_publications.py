import pytest
from lbrc_flask.pytest.testers import IndexTester, RequiresLoginTester, PagedResultSet, PanelListContentAsserter, RowContentAsserter


class PublicationsIndexTester:
    @property
    def endpoint(self):
        return 'ui.publications'


class PublicationsRowContentAsserter(PanelListContentAsserter):
    def assert_row_details(self, row, expected_result):
        assert row is not None
        assert expected_result is not None

    # Todo: Add specific assertions for journal row details


class TestPublicationsRequiresLogin(PublicationsIndexTester, RequiresLoginTester):
    ...


class TestPublicationsIndex(PublicationsIndexTester, IndexTester):
    @property
    def content_asserter(self) -> RowContentAsserter:
        return PublicationsRowContentAsserter

    @pytest.mark.parametrize("item_count", PagedResultSet.test_page_edges())
    @pytest.mark.parametrize("current_page", PagedResultSet.test_current_pages())
    def test__get__no_filters(self, item_count, current_page):
        self.faker.subtype().create_defaults()
        catalog_publications = self.faker.catalog_publication().get_list(
            save=True,
            item_count=item_count,
        )

        publications = [cp.publication for cp in catalog_publications]

        self.parameters['page'] = current_page

        resp = self.get()

        self.assert_all(
            page_count_helper=PagedResultSet(page=current_page, expected_results=publications),
            resp=resp,
        )

    # Todo: Add more tests for filtering, sorting, etc.
