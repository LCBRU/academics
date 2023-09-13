from flask import render_template, request
from lbrc_flask.charting import BarChart
from lbrc_flask.database import db
from lbrc_flask.forms import SearchForm
from sqlalchemy import distinct, select
from wtforms import MonthField, SelectField, HiddenField, SelectMultipleField

from academics.model import (Academic, Theme)
from academics.publication_searching import nihr_acknowledgement_select_choices, publication_search_query, publication_attribution_query, publication_summary, theme_select_choices

from .. import blueprint


class PublicationSearchForm(SearchForm):
    total = SelectField('Total', choices=[('BRC', 'BRC'), ('Theme', 'Theme'), ('Academic', 'Academic')])
    measure = SelectField('Measure', choices=[('Percentage', 'Percentage'), ('Publications', 'Publications')])
    theme_id = SelectField('Theme')
    nihr_acknowledgement_id = SelectMultipleField('Acknowledgement')
    academic_id = HiddenField()
    main_academic = HiddenField()
    publication_start_month = MonthField('Publication Start Month')
    publication_end_date = MonthField('Publication End Month')
    supress_validation_historic = SelectField(
        'Suppress Historic',
        choices=[(True, 'Yes'), (False, 'No')],
        coerce=lambda x: x == 'True',
        default='True',
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.theme_id.choices = theme_select_choices()
        self.nihr_acknowledgement_id.choices = [('-1', 'Unvalidated')] + nihr_acknowledgement_select_choices()


@blueprint.route("/reports", methods=['GET', 'POST'])
def reports():
    print('A'*100)
    search_form = PublicationSearchForm(formdata=request.args)

    return render_template("ui/reports/reports.html", search_form=search_form, report_defs=get_report_defs(search_form))


def get_report_defs(search_form):
    print('B'*100)
    report_defs = []

    if search_form.total.data == 'Academic':
        print('B1'*100)
        publications = publication_search_query(search_form).alias()
        print('B2'*100)
        attribution = publication_attribution_query()
        print('B3'*100)

        q = select(distinct(attribution.c.academic_id).label('academic_id')).join(
            publications, publications.c.id == attribution.c.scopus_publication_id
        )
        print('B4'*100)

        for a in db.session.execute(q).mappings().all():
            x = search_form.raw_data_as_dict()
            x['academic_id'] = a['academic_id']
            x['main_academic'] = 'True'
            x['supress_validation_historic'] = search_form.supress_validation_historic.data
            report_defs.append(x)
        print('B-'*100)
    else:
        x = search_form.raw_data_as_dict()
        x['supress_validation_historic'] = search_form.supress_validation_historic.data
        report_defs.append(x)
        print('B*'*100)

    return report_defs


@blueprint.route("/reports/image")
def report_image():
    print('C'*100)
    search_form = PublicationSearchForm(formdata=request.args)
    print('D'*100)

    if search_form.has_value('academic_id'):
        a : Academic = Academic.query.get_or_404(search_form.academic_id.data)

        title = f'{a.full_name} Publications by Acknowledgement Status'
    elif search_form.has_value('theme_id') or search_form.total.data == "Theme":
        title = 'Theme Publications by Acknowledgement Status'
    else:
        title = 'BRC Publications by Acknowledgement Status'

    if search_form.measure.data == 'Publications':
        title += " Count"
        y_title = 'Publications'
        show_total = True
    else:
        title += " Percentage"
        y_title = 'Percentage'
        show_total = False

    bc: BarChart = BarChart(
        title=title,
        items=publication_summary(search_form),
        y_title=y_title,
        show_total=show_total,
    )

    if search_form.measure.data == 'Percentage':
        bc.value_formatter = lambda x: f'{x}%'

    return bc.send_as_attachment()
