import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester, ModalContentAsserter, ModalFormErrorContentAsserter
from lbrc_flask.pytest.asserts import assert__refresh_response
from lbrc_flask.pytest.form_tester import FormTester, FormTesterTextField, FormTesterCheckboxField, FormTesterTextAreaField, FormTesterField


class FolderAddDoisViewTester:
    @property
    def endpoint(self):
        return 'ui.folder_add_dois'


class FolderAddDoisFormTester(FormTester):
    def __init__(self, has_csrf=False):
        super().__init__(
            fields=[
                FormTesterCheckboxField(
                    field_name='skip_invalid',
                    field_title='Skip Invalid DOIs',
                ),
                FormTesterTextAreaField(
                    field_name='dois_combined',
                    field_title='DOIs',
                ),
            ],
            has_csrf=has_csrf,
        )


class TestFolderAddDoisRequiresLogin(FolderAddDoisViewTester, RequiresLoginTester):
    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.folder = faker.folder().get(save=True)
        self.parameters['id'] = self.folder.id


class TestFolderAddDoisGet(FolderAddDoisViewTester, FlaskViewLoggedInTester):
    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker, login_fixture):
        self.folder = faker.folder().get(save=True, owner_id=self.loggedin_user.id)
        self.parameters['id'] = self.folder.id

    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.get()

        FolderAddDoisFormTester(has_csrf=True).assert_all(resp)
        

class TestFolderAddDoisPost(FolderAddDoisViewTester, FlaskViewLoggedInTester):
    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker, login_fixture):
        self.folder = faker.folder().get(save=True, owner_id=self.loggedin_user.id)
        self.parameters['id'] = self.folder.id

    def test__post__valid(self):
        resp = self.post()

        assert__refresh_response(resp)

    # Todo: Add more tests for invalid data, etc.
