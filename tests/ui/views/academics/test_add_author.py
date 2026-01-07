import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester
from lbrc_flask.pytest.form_tester import FormTester, FormTesterSelectField, FormTesterRadioField
from sqlalchemy import select
from academics.model.theme import Theme
from academics.ui.views.academics import _get_academic_choices
from tests.ui.views.academics import AcademicViewTester
from lbrc_flask.database import db


class AddAuthorFormTester(FormTester):
    def __init__(self, has_csrf=False):
        super().__init__(
            fields=[
                FormTesterSelectField(
                    field_name='academic_id',
                    field_title='Academic',
                    options=dict(_get_academic_choices()),
                ),
                FormTesterRadioField(
                    field_name='themes',
                    field_title='Theme',
                    options=dict([(t.name, str(t.id)) for t in db.session.execute(select(Theme)).scalars()]),
                ),
            ],
            has_csrf=has_csrf,
        )


class AddAuthorViewBaseTester(AcademicViewTester):
    @property
    def endpoint(self):
        return 'ui.add_author'


class TestAddAuthorRequiresLogin(AddAuthorViewBaseTester, RequiresLoginTester):
    ...


class AddAuthorViewTester(AddAuthorViewBaseTester):
    @pytest.fixture(autouse=True)
    def set_editor_user(self, editor_user):
        pass


class TestAddAuthorGet(AddAuthorViewTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.get()

        AddAuthorFormTester(has_csrf=True).assert_all(resp)
