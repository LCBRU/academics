import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester, ModalContentAsserter, ModalFormErrorContentAsserter
from lbrc_flask.pytest.asserts import assert__refresh_response
from lbrc_flask.pytest.form_tester import FormTester, FormTesterTextField, FormTesterCheckboxField, FormTesterTextAreaField, FormTesterField


class FolderAddViewTester:
    @property
    def endpoint(self):
        return 'ui.folder_add'


class FolderAddFormTester(FormTester):
    def __init__(self, has_csrf=False):
        super().__init__(
            fields=[
                FormTesterCheckboxField(
                    field_name='author_access',
                    field_title='Folder Visible to publication authors',
                ),
                FormTesterTextField(
                    field_name='name',
                    field_title='Name',
                    is_mandatory=True,
                ),
                FormTesterTextAreaField(
                    field_name='description',
                    field_title='Description',
                ),
                # Todo: Add more fields
            ],
            has_csrf=has_csrf,
        )


class TestFolderAddRequiresLogin(FolderAddViewTester, RequiresLoginTester):
    ...


class TestFolderAddGet(FolderAddViewTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.get()

        FolderAddFormTester(has_csrf=True).assert_all(resp)
        

class TestFolderAddPost(FolderAddViewTester, FlaskViewLoggedInTester):
    def test__post__valid(self):
        expected = self.faker.folder().get(save=False, owner_id=self.loggedin_user.id)
        data = self.get_data_from_object(expected)

        resp = self.post(data)

        assert__refresh_response(resp)

        assert self.faker.folder().count_in_db() == 1
        actuals = self.faker.folder().all_from_db()

        actual = actuals[0]

        self.faker.folder().assert_equal(expected, actual)

    @pytest.mark.parametrize(
        "missing_field", FolderAddFormTester().mandatory_fields_edit,
    )
    def test__post__missing_mandatory_field(self, missing_field: FormTesterField):
        expected = self.faker.folder().get(save=False, owner_id=self.loggedin_user.id)
        data = self.get_data_from_object(expected)
        data[missing_field.field_name] = ''

        resp = self.post(data)

        FolderAddFormTester().assert_all(resp)
        ModalContentAsserter().assert_all(resp)
        ModalFormErrorContentAsserter().assert_missing_required_field(resp, missing_field.field_title)

        assert self.faker.folder().count_in_db() == 0

    # Todo: Add more tests for invalid data, etc.
