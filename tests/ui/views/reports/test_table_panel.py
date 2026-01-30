import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester, FlaskViewTester


class TablePanelViewBaseTester(FlaskViewTester):
    @property
    def endpoint(self):
        return 'ui.image_panel'
    

class TestTablePanelRequiresLogin(TablePanelViewBaseTester, RequiresLoginTester):
    ...

class TestTablePanelGet(TablePanelViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get(self):
        resp = self.get()

    # Todo: Add more tests for not found, permissions, etc.