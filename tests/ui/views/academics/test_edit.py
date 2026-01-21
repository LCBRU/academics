import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester, ModalContentAsserter, ModalFormErrorContentAsserter
from lbrc_flask.pytest.asserts import assert__refresh_response
from lbrc_flask.pytest.form_tester import FormTesterField
from sqlalchemy import select
from lbrc_flask.database import db
from academics.model.academic import Academic
from tests.ui.views.academics import AcademicFormTester, AcademicViewTester


class AcademicEditViewTester(AcademicViewTester):
    @property
    def endpoint(self):
        return 'ui.academic_edit'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.existing = faker.academic().get_in_db()
        self.parameters['id'] = self.existing.id


class TestAcademicEditRequiresLogin(AcademicEditViewTester, RequiresLoginTester):
    ...


class TestAcademicEditGet(AcademicEditViewTester, FlaskViewLoggedInTester):
    def user_to_login(self, faker):
        return faker.user().editor()

    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.get()

        AcademicFormTester(has_csrf=True).assert_all(resp)
        

class TestAcademicEditPost(AcademicEditViewTester, FlaskViewLoggedInTester):
    def user_to_login(self, faker):
        return faker.user().editor()

    def test__post__valid(self):
        new_user = self.faker.user().get_in_db()
        expected = self.faker.academic().get(user_id=new_user.id, save=False)
        data = self.get_data_from_object(expected)

        resp = self.post(data)

        assert__refresh_response(resp)
        self.assert_db_count(1)

        actual = db.session.execute(select(Academic)).scalar()

        self.assert_actual_equals_expected(expected, actual)

    @pytest.mark.parametrize(
        "missing_field", AcademicFormTester().mandatory_fields_edit,
    )
    def test__post__missing_mandatory_field(self, missing_field: FormTesterField):
        expected = self.faker.academic().get(save=False)
        data = self.get_data_from_object(expected)
        data[missing_field.field_name] = ''

        resp = self.post(data)

        AcademicFormTester().assert_all(resp)
        ModalContentAsserter().assert_all(resp)
        ModalFormErrorContentAsserter().assert_missing_required_field(resp, missing_field.field_title)

        self.assert_db_count(1)
