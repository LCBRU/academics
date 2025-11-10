from itertools import cycle
import re
from flask import url_for
import pytest
from lbrc_flask.pytest.testers import IndexTester, RequiresLoginTester, PanelListContentAsserter, PagedResultSet

from academics.model.academic import Academic


class AcademicIndexTester:
    @property
    def endpoint(self):
        return 'ui.index'

    def sort_academics(self, academics):
        return sorted(academics, key=lambda a: (a.last_name, a.first_name, a.id))


class AcademicNotAdminRowContentAsserter(PanelListContentAsserter):
    def assert_row_details(self, row, expected_result: Academic):
        assert row is not None
        assert expected_result is not None
        assert (header := row.find('header')) is not None
        assert (details := row.find('table')) is not None

        self.assert_header(row, expected_result, header)
        self.assert_details(row, expected_result, details)

    def assert_header(self, row, expected_result: Academic, header):
        assert header.find_all(string=re.compile(expected_result.full_name))

        for t in expected_result.themes:
            assert header.find(string=re.compile(t.name))

        publication_count = header.find('a', attrs={'href': url_for('ui.publications', academic_id=expected_result.id)})
        assert publication_count is not None
        assert f'{expected_result.publication_count} Combined Publications' in publication_count.text

        assert header.find('a', attrs={'href': expected_result.orcid_link}) is not None
        assert header.find('a', attrs={'href': expected_result.google_scholar_link}) is not None
        assert header.find('a', attrs={'href': expected_result.pubmed_link}) is not None

    def assert_details(self, row, expected_result: Academic, header):
        pass


class AcademicEditorRowContentAsserter(AcademicNotAdminRowContentAsserter):
    def assert_header(self, row, expected_result, header):
        super().assert_header(row, expected_result, header)

        assert header.find('a', attrs={'hx-get': url_for('ui.academics_potential_sources', id=expected_result.id)}) is not None
        assert header.find('a', attrs={'hx-get': url_for('ui.academic_edit', id=expected_result.id)}) is not None
        assert header.find('a', attrs={'hx-post': url_for('ui.delete_academic', id=expected_result.id)}) is not None


class TestSiteIndexRequiresLogin(AcademicIndexTester, RequiresLoginTester):
    ...


class TestAcademicIndex(AcademicIndexTester, IndexTester):
    @property
    def content_asserter(self):
        return AcademicNotAdminRowContentAsserter
    
    @pytest.mark.parametrize("item_count", PagedResultSet.test_page_edges())
    @pytest.mark.parametrize("current_page", PagedResultSet.test_current_pages())
    def test__get__no_filters(self, item_count, current_page):
        academics = self.faker.academic().get_list_in_db(item_count=item_count)

        self.parameters['page'] = current_page

        resp = self.get()

        self.assert_all(
            page_count_helper=PagedResultSet(
                page=current_page,
                expected_results=self.sort_academics(academics),
            ),
            resp=resp,
        )

    @pytest.mark.parametrize("item_count", PagedResultSet.test_page_edges())
    @pytest.mark.parametrize("current_page", PagedResultSet.test_current_pages())
    @pytest.mark.parametrize("not_initialised_count", [1, 23])
    def test__get__not_initialised_not_displayed(self, item_count, current_page, not_initialised_count):
        academics = self.faker.academic().get_list_in_db(item_count=item_count)
        not_initialised_academics = self.faker.academic().get_list_in_db(item_count=not_initialised_count, initialised=False)

        self.parameters['page'] = current_page

        resp = self.get()

        self.assert_all(
            page_count_helper=PagedResultSet(
                page=current_page,
                expected_results=self.sort_academics(academics),
            ),
            resp=resp,
        )

    @pytest.mark.parametrize("item_count", PagedResultSet.test_page_edges())
    @pytest.mark.parametrize("current_page", PagedResultSet.test_current_pages())
    @pytest.mark.parametrize("count_without", [1, 23])
    def test__get__first_name(self, item_count, current_page, count_without):
        search_name = 'fred'
        first_names = cycle(['fred', 'freddy', 'alfred'])

        academics = []
        print(item_count)
        for i in range(item_count):
            academics.append(
                self.faker.academic().get_in_db(first_name=next(first_names), last_name='smith')
            )

        academics_without = self.faker.academic().get_list_in_db(item_count=count_without, first_name='John', last_name='Smith')

        self.parameters['page'] = current_page
        self.parameters['search'] = search_name

        resp = self.get()

        self.assert_all(
            page_count_helper=PagedResultSet(
                page=current_page,
                expected_results=self.sort_academics(academics),
            ),
            resp=resp,
        )


    @pytest.mark.parametrize("item_count", PagedResultSet.test_page_edges())
    @pytest.mark.parametrize("current_page", PagedResultSet.test_current_pages())
    @pytest.mark.parametrize("count_without", [1, 23])
    def test__get__other_searches(self, item_count, current_page, count_without):
        assert False


    @pytest.mark.parametrize("item_count", PagedResultSet.test_page_edges())
    @pytest.mark.parametrize("current_page", PagedResultSet.test_current_pages())
    @pytest.mark.parametrize("count_without", [1, 23])
    def test__get__different_numbers_of_sources(self, item_count, current_page, count_without):
        assert False


class TestAcademicEditorIndex(AcademicIndexTester, IndexTester):
    @property
    def content_asserter(self):
        return AcademicEditorRowContentAsserter
    
    @pytest.fixture(autouse=True)
    def set_user_as_editor(self, editor_user):
        ...

    @pytest.mark.parametrize("item_count", PagedResultSet.test_page_edges())
    @pytest.mark.parametrize("current_page", PagedResultSet.test_current_pages())
    def test__get__no_filters(self, item_count, current_page):
        academics = self.faker.academic().get_list_in_db(item_count=item_count)

        self.parameters['page'] = current_page

        resp = self.get()

        self.assert_all(
            page_count_helper=PagedResultSet(
                page=current_page,
                expected_results=self.sort_academics(academics),
            ),
            resp=resp,
        )

