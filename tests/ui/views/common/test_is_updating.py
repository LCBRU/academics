from unittest.mock import patch
import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester


class IsUpdatingViewTester:
    @property
    def endpoint(self):
        return 'ui.is_updating'


class TestIsUpdatingRequiresLogin(IsUpdatingViewTester, RequiresLoginTester):
    ...


class TestIsUpdatingGet(IsUpdatingViewTester, FlaskViewLoggedInTester):
    def test__get(self):
        resp = self.get()

        # To do: Add tests for checking content
