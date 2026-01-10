import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class ExportDashboardReportXlsxViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.publication_dashboard_report_xlsx'


class TestDashboardReportXlsxRequiresLogin(ExportDashboardReportXlsxViewBaseTester, RequiresLoginTester):
    ...


class TestDashboardReportXlsxGet(ExportDashboardReportXlsxViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get(self):
        resp = self.get()

    # To do: test the actual content of the XLSX file
