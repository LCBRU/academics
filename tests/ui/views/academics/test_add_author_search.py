import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from lbrc_flask.pytest.form_tester import FormTester, FormTesterSearchField, FormTesterCheckboxField
from tests.ui.views.academics import AcademicViewTester


class AddAuthorSearchFormTester(FormTester):
    def __init__(self, has_csrf=False):
        super().__init__(
            fields=[
                FormTesterSearchField(has_clear=False),
                FormTesterCheckboxField(
                    field_name='show_non_local',
                    field_title='Show Non-Local',
                ),
            ],
            has_csrf=has_csrf,
        )


class AddAuthorSearchViewBaseTester(AcademicViewTester):
    @property
    def endpoint(self):
        return 'ui.add_author_search'


class TestAddAuthorSearchRequiresLogin(AddAuthorSearchViewBaseTester, RequiresLoginTester):
    ...


class AddAuthorSearchViewTester(AddAuthorSearchViewBaseTester):
    @pytest.fixture(autouse=True)
    def set_editor_user(self, editor_user):
        pass


class TestAddAuthorSearchGet(AddAuthorSearchViewTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.get()

        AddAuthorSearchFormTester(has_csrf=False).assert_all(resp)
