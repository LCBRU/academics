from datetime import UTC, datetime
from random import choice
import pytest
from lbrc_flask.pytest.testers import IndexTester, RequiresLoginTester, PagedResultSet, PanelListContentAsserter, RowContentAsserter

from academics.model.publication import Subtype
from academics.model.catalog import validation_catalogs


class ValidationIndexTester:
    @property
    def endpoint(self):
        return 'ui.validation'


class ValidationRowContentAsserter(PanelListContentAsserter):
    def assert_row_details(self, row, expected_result):
        assert row is not None
        assert expected_result is not None

    # Todo: Add specific assertions for journal row details


class TestValidationRequiresLogin(ValidationIndexTester, RequiresLoginTester):
    ...


class TestValidationIndex(ValidationIndexTester, IndexTester):
    def assert_search_form(self, resp):
        pass # This view has no search form

    def user_to_login(self, faker):
        return faker.user().validator(save=True)

    @property
    def content_asserter(self) -> RowContentAsserter:
        return ValidationRowContentAsserter

    @pytest.mark.parametrize("item_count", PagedResultSet.test_page_edges())
    @pytest.mark.parametrize("current_page", PagedResultSet.test_current_pages())
    def test__get__no_filters(self, item_count, current_page):
        self.faker.subtype().create_defaults()

        publications = self.faker.publication().get_list(
            save=True,
            item_count=item_count,
            nihr_acknowledgement=None,
        )

        for p in publications:
            cat_pub = self.faker.catalog_publication().get(
                save=True,
                publication=p,
                catalog=lambda: choice(validation_catalogs),
                subtype_id=lambda: choice(Subtype.get_validation_types()).id,
                publication_cover_date=datetime.now(UTC),
            )

            print(cat_pub.publication_cover_date)
            print(cat_pub.subtype_id)

        self.parameters['page'] = current_page

        resp = self.get()

        self.assert_all(
            page_count_helper=PagedResultSet(page=current_page, expected_results=publications),
            resp=resp,
        )

    # Todo: Add more tests for filtering, sorting, etc.
