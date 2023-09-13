from flask import render_template, request
from lbrc_flask.charting import BarChart
from lbrc_flask.database import db
from lbrc_flask.forms import SearchForm
from sqlalchemy import distinct, select
from wtforms import MonthField, SelectField, HiddenField, SelectMultipleField

from academics.model import (Academic, NihrAcknowledgement, Theme)
from academics.publication_searching import publication_search_query, publication_attribution_query, publication_summary

from .. import blueprint

def _get_nihr_acknowledgement_choices():
    return [(f.id, f.name.title()) for f in NihrAcknowledgement.query.order_by(NihrAcknowledgement.name).all()]


class PublicationSearchForm(SearchForm):
    total = SelectField('Total', choices=[('BRC', 'BRC'), ('Theme', 'Theme'), ('Academic', 'Academic')])
    measure = SelectField('Measure', choices=[('Percentage', 'Percentage'), ('Publications', 'Publications')])
    theme_id = SelectField('Theme')
    nihr_acknowledgement_id = SelectMultipleField('Acknowledgement')
    main_academic_id = HiddenField()
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

        self.theme_id.choices = [('', '')] + [(t.id, t.name) for t in Theme.query.all()]
        self.nihr_acknowledgement_id.choices = [('-1', 'Unvalidated')] + _get_nihr_acknowledgement_choices()


@blueprint.route("/reports", methods=['GET', 'POST'])
def reports():
    search_form = PublicationSearchForm(formdata=request.args)

    return render_template("ui/reports/reports.html", search_form=search_form, report_defs=get_report_defs(search_form))


def get_report_defs(search_form):
    report_defs = []

    if search_form.total.data == 'Academic':
        publications = publication_search_query(search_form).alias()
        attribution = publication_attribution_query()

        q = select(distinct(attribution.c.academic_id).label('academic_id')).join(
            publications, publications.c.id == attribution.c.scopus_publication_id
        )

        for a in db.session.execute(q).mappings().all():
            x = search_form.raw_data_as_dict()
            x['main_academic_id'] = a['academic_id']
            x['supress_validation_historic'] = search_form.supress_validation_historic.data
            report_defs.append(x)
    else:
        x = search_form.raw_data_as_dict()
        x['supress_validation_historic'] = search_form.supress_validation_historic.data
        report_defs.append(x)

    return report_defs


@blueprint.route("/reports/image")
def report_image():
    search_form = PublicationSearchForm(formdata=request.args)

    if search_form.has_value('main_academic_id'):
        a : Academic = Academic.query.get_or_404(search_form.main_academic_id.data)

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
