import pytest
from lbrc_flask.pytest.testers import IndexTester, RequiresLoginTester


class PublicationFolderSearchResultsTester:
    @property
    def endpoint(self):
        return 'ui.publication_folder_search_results'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.publication = faker.publication().get(save=True)
        self.catalog_publication = faker.catalog_publication().get(save=True, publication=self.publication)
        self.parameters['publication_id'] = self.publication.id


class TestPublicationFolderSearchResultsRequiresLogin(PublicationFolderSearchResultsTester, RequiresLoginTester):
    ...


class TestPublicationFolderSearchResults(PublicationFolderSearchResultsTester, IndexTester):
    def test__post(self):
        resp = self.get()

        # Todd: Add tests check content
