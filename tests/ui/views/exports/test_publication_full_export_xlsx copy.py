import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class ExportFullExportXlsxViewBaseTester:
    @property
    def endpoint(self):
        return 'ui.publication_full_export_xlsx'


class TestExportFullExportXlsxRequiresLogin(ExportFullExportXlsxViewBaseTester, RequiresLoginTester):
    ...


class TestExportFullExportXlsxGet(ExportFullExportXlsxViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get(self):
        resp = self.get()
