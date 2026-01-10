import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class ExportFullAnnualReportXlsxViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.publication_full_annual_report_xlsx'


class TestExportFullAnnualReportXlsxRequiresLogin(ExportFullAnnualReportXlsxViewBaseTester, RequiresLoginTester):
    ...


class TestExportFullAnnualReportXlsxGet(ExportFullAnnualReportXlsxViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get(self):
        resp = self.get()

    # To do: test the actual content of the XLSX file
