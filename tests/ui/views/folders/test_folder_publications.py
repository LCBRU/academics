import pytest
from lbrc_flask.pytest.testers import IndexTester, RequiresLoginTester, PagedSize10ResultSet, PanelListContentAsserter, RowContentAsserter


class FolderPublicationsTester:
    @property
    def endpoint(self):
        return 'ui.folder_publications'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        faker.subtype().create_defaults()
        self.folder = faker.folder().get(save=True)
        self.parameters['folder_id'] = self.folder.id


class FolderPublicationsRowContentAsserter(PanelListContentAsserter):
    def assert_row_details(self, row, expected_result):
        assert row is not None
        assert expected_result is not None

        # Todo: Add specific assertions for folder row details


class TestFolderPublicationsRequiresLogin(FolderPublicationsTester, RequiresLoginTester):
    ...


class TestFolderPublications(FolderPublicationsTester, IndexTester):
    @property
    def content_asserter(self) -> RowContentAsserter:
        return FolderPublicationsRowContentAsserter

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker, login_fixture):
        faker.subtype().create_defaults()
        self.folder = faker.folder().get(save=True, owner_id=self.loggedin_user.id)
        self.parameters['folder_id'] = self.folder.id

    @pytest.mark.parametrize("item_count", PagedSize10ResultSet.test_page_edges())
    @pytest.mark.parametrize("current_page", PagedSize10ResultSet.test_current_pages())
    def test__get__no_filters(self, item_count, current_page):
        cat_pubs = self.faker.catalog_publication().get_list(
            save=True,
            item_count=item_count,
        )

        for cp in cat_pubs:
            self.faker.folder_doi().get(
                save=True,
                folder_id=self.folder.id,
                doi=cp.doi,
            )

        self.parameters['page'] = current_page

        resp = self.get()

        self.assert_all(
            page_count_helper=PagedSize10ResultSet(page=current_page, expected_results=cat_pubs),
            resp=resp,
        )

    # Todo: Add more tests for filtering, sorting, etc.
