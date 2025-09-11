import pytest
from lbrc_flask.pytest.testers import RequiresLoginGetTester, FlaskPostViewTester, FlaskFormGetViewTester
from lbrc_flask.pytest.asserts import assert__refresh_response
from lbrc_flask.pytest.form_tester import FormTesterField
from sqlalchemy import select
from lbrc_flask.database import db
from tests.ui.views.academics import AcademicFormTester, AcademicViewTester


class AcademicEditViewBaseTester(AcademicViewTester):
    @property
    def endpoint(self):
        return 'ui.academic_edit'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.existing = faker.academic().get_in_db()
        self.parameters = dict(id=self.existing.id)


class TestAcademicEditRequiresLogin(AcademicEditViewBaseTester, RequiresLoginGetTester):
    ...


class AcademicEditViewTester(AcademicEditViewBaseTester):
    @pytest.fixture(autouse=True)
    def set_editor_user(self, editor_user):
        pass


class TestAcademicEditGet(AcademicEditViewTester, FlaskFormGetViewTester):
    ...


class TestAcademicEditPost(AcademicEditViewTester, FlaskPostViewTester):
    def test__post__valid(self):
        expected = self.item_creator.get(packtype=None, pack_shipment=None, pack_action=None)

        expected.packtype_id = self.standard_packtypes[0].id
        data = self.get_data_from_object(expected)
        data['pack_type'] = str(expected.packtype_id)

        resp = self.post(data)

        assert__refresh_response(resp)
        self.assert_db_count(1)

        actual = db.session.execute(select(Pack)).scalar()

        self.assert_actual_equals_expected(expected, actual)

    @pytest.mark.parametrize(
        "missing_field", AcademicFormTester().mandatory_fields_edit,
    )
    def test__post__missing_mandatory_field(self, missing_field: FormTesterField):
        expected = self.item_creator.get(packtype=None, pack_shipment=None, pack_action=None)
        data = self.get_data_from_object(expected)
        data[missing_field.field_name] = ''

        resp = self.post(data)

        self.assert_standards(resp)
        self.assert_form(resp.soup)
        self.assert__error__required_field(resp, missing_field.field_title)
        self.assert_db_count(1)
