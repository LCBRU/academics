import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


# class FolderDoiDeleteViewBaseTester:
#     @property
#     def endpoint(self):
#         return 'ui.folderdoi_delete'

#     @pytest.fixture(autouse=True)
#     def set_existing(self, client, faker):
#         self.folder_doi = faker.folder_doi().get(save=False)
#         self.parameters['folder_id'] = self.folder_doi.folder.id
#         self.parameters['doi'] = self.folder_doi.doi


# class TestFolderDoiDeleteRequiresLogin(FolderDoiDeleteViewBaseTester, RequiresLoginTester):
#     ...


# class TestFolderDoiDeleteGet(FolderDoiDeleteViewBaseTester, FlaskViewLoggedInTester):
#     @pytest.mark.app_crsf(True)
#     def test__get(self):
#         resp = self.get()

#     # To do: add more tests here
