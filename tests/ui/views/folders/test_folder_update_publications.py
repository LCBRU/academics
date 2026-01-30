import pytest
from unittest.mock import patch
from lbrc_flask.pytest.testers import IndexTester, RequiresLoginTester, PagedResultSet, TableContentAsserter, RowContentAsserter
from lbrc_flask.pytest.asserts import assert__refresh_response


class FolderUpdatePublicationsTester:
    @property
    def endpoint(self):
        return 'ui.folder_update_publications'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.folder = faker.folder().get(save=True, owner_id=self.user_to_login(faker).id)
        self.parameters['id'] = self.folder.id


class TestFolderUpdatePublicationsRequiresLogin(FolderUpdatePublicationsTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestFolderUpdatePublications(FolderUpdatePublicationsTester, IndexTester):
    @patch('academics.services.folder.run_jobs_asynch') # Mocking as cereal tasks do not work in testing
    def test__post(self, run_jobs_asynch):
        resp = self.post()

        assert__refresh_response(resp)

        # Todd: Add tests to check publications are set for updating
