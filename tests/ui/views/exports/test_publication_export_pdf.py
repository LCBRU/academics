import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class ExportPublicationExportPDFViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.publication_export_pdf'


class TestPublicationExportPDFRequiresLogin(ExportPublicationExportPDFViewBaseTester, RequiresLoginTester):
    ...


class TestPublicationExportPDFGet(ExportPublicationExportPDFViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get(self):
        resp = self.get()

    # To do: test the actual content of the PDF file
