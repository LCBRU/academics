from lbrc_flask.pytest.form_tester import FormTester, FormTesterTextField, FormTesterSelectField, FormTesterEmailField
from lbrc_flask.database import db
from sqlalchemy import select
from academics.model.theme import Theme


class UserEditFormTester(FormTester):
    def __init__(self, has_csrf=False):
        super().__init__(
            fields=[
                FormTesterEmailField(
                    field_name='email',
                    field_title='Email',
                    is_mandatory=True,
                ),
                FormTesterTextField(
                    field_name='first_name',
                    field_title='First Name',
                    is_mandatory=True,
                ),
                FormTesterTextField(
                    field_name='last_name',
                    field_title='Last Name',
                    is_mandatory=True,
                ),
                FormTesterSelectField(
                    field_name='theme',
                    field_title='Theme',
                    options=dict([('0', '')] + [(str(t.id), t.name) for t in db.session.execute(select(Theme)).scalars()]),
                ),
            ],
            has_csrf=has_csrf,
        )