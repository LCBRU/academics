from sqlalchemy import func, select
from lbrc_flask.database import db
from lbrc_flask.pytest.form_tester import FormTester, FormTesterTextField

from academics.model.academic import Academic


class AcademicFormTester(FormTester):
    def __init__(self, has_csrf=False):
        super().__init__(
            fields=[
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
                FormTesterTextField(
                    field_name='initials',
                    field_title='Initials',
                ),
                FormTesterTextField(
                    field_name='orcid',
                    field_title='ORCID',
                ),
                FormTesterTextField(
                    field_name='google_scholar_id',
                    field_title='Google Scholar ID',
                ),
            ],
            has_csrf=has_csrf,
        )


class AcademicViewTester:
    @property
    def item_creator(self):
        return self.faker.academic()
    
    def assert_db_count(self, expected_count):
        assert db.session.execute(select(func.count(Academic.id))).scalar() == expected_count

    def assert_actual_equals_expected(self, expected: Academic, actual: Academic):
        assert actual is not None
        assert expected is not None

        actual.first_name == expected.first_name
        actual.last_name == expected.last_name
        actual.initials == expected.initials
        actual.orcid == expected.orcid
        actual.google_scholar_id == expected.google_scholar_id
        actual.updating == expected.updating
        actual.initialised == expected.initialised
        actual.error == expected.error
        actual.has_left_brc == expected.has_left_brc
        actual.left_brc_date == expected.left_brc_date

        if actual.user is None:
            actual_user_id = actual.user_id
        else:
            actual_user_id = actual.user.id

        if expected.user is None:
            expected_user_id = expected.user_id
        else:
            expected_user_id = expected.user.id

        assert actual_user_id == expected_user_id
