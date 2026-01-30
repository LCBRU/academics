import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester, FlaskViewTester


class ImagePanelViewBaseTester(FlaskViewTester):
    @property
    def endpoint(self):
        return 'ui.image_panel'
    

class TestImagePanelRequiresLogin(ImagePanelViewBaseTester, RequiresLoginTester):
    ...

class TestImagePanelGet(ImagePanelViewBaseTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get(self):
        resp = self.get()

    # Todo: Add more tests for not found, permissions, etc.