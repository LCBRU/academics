import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester, FlaskViewTester


class AcademicsExportCsvViewBaseTester(FlaskViewTester):
    @property
    def endpoint(self):
        return 'ui.academics_export_csv'
    

class TestAcademicsExportCsvRequiresLogin(AcademicsExportCsvViewBaseTester, RequiresLoginTester):
    ...

class TestAcademicsExportCsvGet(AcademicsExportCsvViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get(self):
        resp = self.get()

    # Todo: Add more tests for not found, permissions, etc.