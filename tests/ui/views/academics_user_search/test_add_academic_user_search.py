import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from lbrc_flask.pytest.form_tester import FormTester, FormTesterSearchField


class AcademicUserSearchFormTester(FormTester):
    def __init__(self, has_csrf=False):
        super().__init__(
            fields=[
                FormTesterSearchField(
                    field_name='search_string',
                    has_clear=False,
                    has_submit=False,
                ),
            ],
            has_csrf=has_csrf,
        )


class AcademicUserSearchViewTester:
    @property
    def endpoint(self):
        return 'ui.academic_user_search'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.existing = faker.academic().get_in_db()
        self.parameters['academic_id'] = self.existing.id


class TestAcademicUserSearchRequiresLogin(AcademicUserSearchViewTester, RequiresLoginTester):
    ...


class TestAcademicUserSearchGet(AcademicUserSearchViewTester, FlaskViewLoggedInTester):
    def user_to_login(self, faker):
        return faker.user().editor()

    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.get()

        AcademicUserSearchFormTester(has_csrf=False).assert_all(resp)
