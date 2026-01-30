import pytest
from lbrc_flask.pytest.testers import IndexTester, RequiresLoginTester


class FolderAcademicsTester:
    @property
    def endpoint(self):
        return 'ui.folder_academics'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.folder = faker.folder().get(save=True, owner_id=self.user_to_login(faker).id)
        self.parameters['folder_id'] = self.folder.id


class TestFolderAcademicsRequiresLogin(FolderAcademicsTester, RequiresLoginTester):
    ...


class TestFolderAcademics(FolderAcademicsTester, IndexTester):
    def test__get(self):
        resp = self.get()

    # Todo: I think that this page will be deleted soon, so I'm
    # not going to add more tests for now.
