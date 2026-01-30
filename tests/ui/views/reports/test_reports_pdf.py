import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester, FlaskViewTester


class ReportsPdfViewBaseTester(FlaskViewTester):
    @property
    def endpoint(self):
        return 'ui.reports_pdf'
    

class TestReportsPdfRequiresLogin(ReportsPdfViewBaseTester, RequiresLoginTester):
    ...


class TestRepostsPdfGet(ReportsPdfViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get(self):
        resp = self.get()

    # Todo: Add more tests for not found, permissions, etc.