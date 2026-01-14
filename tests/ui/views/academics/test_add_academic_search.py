import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from lbrc_flask.pytest.form_tester import FormTester, FormTesterSearchField, FormTesterCheckboxField
from academics.security import ROLE_EDITOR
from tests.ui.views.academics import AcademicViewTester


class AddAcademicSearchFormTester(FormTester):
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


class AddAcademicSearchViewBaseTester(AcademicViewTester):
    @property
    def endpoint(self):
        return 'ui.add_author_search'


class TestAddAcademicSearchRequiresLogin(AddAcademicSearchViewBaseTester, RequiresLoginTester):
    ...


class TestAddAcademicSearchGet(AddAcademicSearchViewBaseTester, FlaskViewLoggedInTester):
    def user_to_login(self, faker):
        return faker.user().get_in_db(rolename=ROLE_EDITOR)

    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.get()

        AddAcademicSearchFormTester(has_csrf=False).assert_all(resp)
