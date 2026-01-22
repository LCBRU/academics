import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class FolderDoiDeleteViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.folderdoi_delete'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.folder_doi = faker.folder_doi().get(save=True)
        self.parameters['folder_id'] = self.folder_doi.folder.id
        self.parameters['doi'] = self.folder_doi.doi


class TestFolderDoiDeleteRequiresLogin(FolderDoiDeleteViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestFolderDoiDeleteGet(FolderDoiDeleteViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__post(self):
        resp = self.post()

        assert self.faker.folder_doi().get_by_id(self.folder_doi.id) is None

    @pytest.mark.app_crsf(True)
    def test__post__not_found(self):
        self.parameters['doi'] = '10.9999/nonexistent'
        resp = self.post()

        assert self.faker.folder_doi().get_by_id(self.folder_doi.id) is not None
