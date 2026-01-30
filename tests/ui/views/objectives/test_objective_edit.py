import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester, ModalContentAsserter, ModalFormErrorContentAsserter, FlaskViewTester
from lbrc_flask.pytest.asserts import assert__refresh_response
from lbrc_flask.pytest.form_tester import FormTester, FormTesterTextField, FormTesterField


class ObjectiveEditViewTester(FlaskViewTester):
    @property
    def endpoint(self):
        return 'ui.objective_edit'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.objective = faker.objective().get(save=True, owner_id=self.user_to_login(faker).id)
        self.parameters['id'] = self.objective.id


class ObjectiveEditFormTester(FormTester):
    def __init__(self, has_csrf=False):
        super().__init__(
            fields=[
                FormTesterTextField(
                    field_name='name',
                    field_title='Name',
                    is_mandatory=True,
                ),
                # Add other fields as necessary
            ],
            has_csrf=has_csrf,
        )


class TestObjectiveEditRequiresLogin(ObjectiveEditViewTester, RequiresLoginTester):
    ...

class TestObjectiveEditGet(ObjectiveEditViewTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.get()

        ObjectiveEditFormTester(has_csrf=True).assert_all(resp)
        

class TestObjectiveEditPost(ObjectiveEditViewTester, FlaskViewLoggedInTester):
    def test__post__valid(self):
        theme = self.faker.theme().get(save=True)
        expected = self.faker.objective().get(save=False, owner_id=self.loggedin_user.id, theme_id=theme.id)
        data = self.get_data_from_object(expected)

        resp = self.post(data)

        assert__refresh_response(resp)

        assert self.faker.objective().count_in_db() == 1
        actuals = self.faker.objective().all_from_db()

        actual = actuals[0]

        self.faker.objective().assert_equal(expected, actual)

    @pytest.mark.parametrize(
        "missing_field", ObjectiveEditFormTester().mandatory_fields_edit,
    )
    def test__post__missing_mandatory_field(self, missing_field: FormTesterField):
        expected = self.faker.objective().get(save=False, owner_id=self.loggedin_user.id)
        data = self.get_data_from_object(expected)
        data[missing_field.field_name] = ''

        resp = self.post(data)

        ObjectiveEditFormTester().assert_all(resp)
        ModalContentAsserter().assert_all(resp)
        ModalFormErrorContentAsserter().assert_missing_required_field(resp, missing_field.field_title)

        assert self.faker.objective().count_in_db() == 1

    # Todo: Add more tests for invalid data, etc.
