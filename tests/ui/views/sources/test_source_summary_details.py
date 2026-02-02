import pytest
from lbrc_flask.pytest.testers import RequiresLoginTester, FlaskViewLoggedInTester, ModalContentAsserter, ModalFormErrorContentAsserter
from lbrc_flask.pytest.asserts import assert__refresh_response
from lbrc_flask.pytest.form_tester import FormTester, FormTesterSelectField, FormTesterField

from academics.ui.views.academics import _get_academic_choices


class SourceSummaryDetailsViewTester:
    @property
    def endpoint(self):
        return 'ui.source_summary_details'

    @pytest.fixture(autouse=True)
    def set_existing(self, client, faker):
        self.academic = faker.academic().get(save=True)
        self.source = faker.source().get(save=True)
        self.parameters['id'] = self.source.id

    def academic_options(self):
        return dict([(0, '')] + [(self.academic.id, self.academic.full_name)])


class SourceSummaryDetailsFormTester(FormTester):
    def __init__(self, has_csrf=False, academic_options=None):
        academic_options = academic_options or dict([])

        super().__init__(
            fields=[
                FormTesterSelectField(
                    field_name='academic_id',
                    field_title='Other Academic',
                    options=academic_options,
                ),
            ],
            has_csrf=has_csrf,
        )


class TestSourceSummaryDetailsRequiresLogin(SourceSummaryDetailsViewTester, RequiresLoginTester):
    ...


class TestSourceSummaryDetailsEditGet(SourceSummaryDetailsViewTester, FlaskViewLoggedInTester):
    @pytest.mark.app_crsf(True)
    def test__get__has_form(self):
        resp = self.get()

        SourceSummaryDetailsFormTester(
            has_csrf=True,
            academic_options=self.academic_options(),
        ).assert_all(resp)
        

class TestSourceSummaryDetailsEditPost(SourceSummaryDetailsViewTester, FlaskViewLoggedInTester):
    def test__post__valid(self):
        expected = self.faker.source().get(save=False, academic_id=self.academic.id)
        data = self.get_data_from_object(expected)

        print(data)

        resp = self.post(data, debug=True)

        assert__refresh_response(resp)

        assert self.faker.source().count_in_db() == 1
        actuals = self.faker.source().all_from_db()

        actual = actuals[0]

        self.faker.source().assert_equal(expected, actual)

    # Todo: Add more tests for invalid data, etc.
