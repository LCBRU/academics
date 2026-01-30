import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester, ModalContentAsserter, ModalFormErrorContentAsserter
from lbrc_flask.pytest.asserts import assert__refresh_response
from lbrc_flask.pytest.form_tester import FormTester, FormTesterTextField, FormTesterField, FormTesterTextAreaField, FormTesterDateField


class CatalogPublicationEditViewTester:
    @property
    def endpoint(self):
        return 'ui.catalog_publication_edit'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.catalog_publication = faker.catalog_publication().get(save=True)
        self.parameters['id'] = self.catalog_publication.id



class CatalogPublicationEditFormTester(FormTester):
    def __init__(self, has_csrf=False):
        super().__init__(
            fields=[
                FormTesterTextField(
                    field_name='doi',
                    field_title='DOI',
                    is_mandatory=True,
                ),
                FormTesterTextAreaField(
                    field_name='title',
                    field_title='Title',
                ),
                FormTesterDateField(
                    field_name='publication_cover_date',
                    field_title='Publication Cover Date',
                ),
            ],
            has_csrf=has_csrf,
        )


class TestCatalogPublicationEditRequiresLogin(CatalogPublicationEditViewTester, RequiresLoginTester):
    ...


class TestCatalogPublicationEditGet(CatalogPublicationEditViewTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.get()

        CatalogPublicationEditFormTester(has_csrf=True).assert_all(resp)
        

class TestCatalogPublicationEditPost(CatalogPublicationEditViewTester, FlaskViewLoggedInTester):
    def test__post__valid(self):
        expected = self.faker.catalog_publication().get(save=False)
        data = self.get_data_from_object(expected)

        resp = self.post(data)

        assert__refresh_response(resp)

        assert self.faker.catalog_publication().count_in_db() == 1
        actuals = self.faker.catalog_publication().all_from_db()

        actual = actuals[0]

        self.faker.catalog_publication().assert_equal(expected, actual)

    @pytest.mark.parametrize(
        "missing_field", CatalogPublicationEditFormTester().mandatory_fields_edit,
    )
    def test__post__missing_mandatory_field(self, missing_field: FormTesterField):
        expected = self.faker.catalog_publication().get(save=False)
        data = self.get_data_from_object(expected)
        data[missing_field.field_name] = ''

        resp = self.post(data)

        CatalogPublicationEditFormTester().assert_all(resp)
        ModalContentAsserter().assert_all(resp)
        ModalFormErrorContentAsserter().assert_missing_required_field(resp, missing_field.field_title)

        assert self.faker.catalog_publication().count_in_db() == 1

    # Todo: Add more tests for invalid data, etc.
