import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester, FlaskViewTester


class ReportImageViewBaseTester(FlaskViewTester):
    @property
    def endpoint(self):
        return 'ui.report_image'
    

class TestReportImageRequiresLogin(ReportImageViewBaseTester, RequiresLoginTester):
    ...

class TestReportImageGet(ReportImageViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get(self):
        resp = self.get()

    # Todo: Add more tests for not found, permissions, etc.