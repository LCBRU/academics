import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class ExportPublicationAuthorReportPDFViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.publication_author_report_pdf'


class TestPublicationAuthorReportPDFRequiresLogin(ExportPublicationAuthorReportPDFViewBaseTester, RequiresLoginTester):
    ...


class TestPublicationAuthorReportPDFGet(ExportPublicationAuthorReportPDFViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get(self):
        resp = self.get()

    # To do: test the actual content of the PDF file
