import http
import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from lbrc_flask.database import db

class PublicationsCreateFolderViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.publication_create_folder'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        faker.subtype().create_defaults()
        self.publication = faker.publication().get(save=True, folders=[])
        self.catalog_publication = faker.catalog_publication().get(
            save=True,
            publication=self.publication,
        )
        db.session.commit()


class TestPublicationCreatFolderRequiresLogin(PublicationsCreateFolderViewBaseTester, RequiresLoginTester):
    @property
    def request_method(self):
        return self.post


class TestPublicationCreateFolderGet(PublicationsCreateFolderViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__post__no_filters(self):
        resp = self.post(expected_status_code=http.HTTPStatus.FOUND)

        self.assert_redirect(resp, 'ui.folders')

        assert self.faker.folder().count_in_db() == 1
        folder = self.faker.folder().all_from_db()[0]
        assert folder.name.startswith('Publication Search ')
        assert len(folder.dois) == 1
        dois = [fd.doi for fd in folder.dois]
        assert self.publication.doi in dois
