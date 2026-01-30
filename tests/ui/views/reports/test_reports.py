import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester, FlaskViewTester


class ReportsViewBaseTester(FlaskViewTester):
    @property
    def endpoint(self):
        return 'ui.reports'
    

class TestReportsRequiresLogin(ReportsViewBaseTester, RequiresLoginTester):
    ...

class TestReportsGet(ReportsViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get(self):
        resp = self.get()

    # Todo: Add more tests for not found, permissions, etc.