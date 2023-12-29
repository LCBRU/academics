from flask import render_template, request
from lbrc_flask.charting import BarChart
from lbrc_flask.database import db
from lbrc_flask.forms import SearchForm
from sqlalchemy import distinct, select
from wtforms import MonthField, SelectField, HiddenField, SelectMultipleField
from lbrc_flask.export import csv_download
from sqlalchemy import select

from academics.model import Academic, CatalogPublication, CatalogPublicationsSources, Publication, PublicationsSources, Source
from academics.publication_searching import nihr_acknowledgement_select_choices, publication_count, publication_search_query, publication_summary, theme_select_choices

from .. import blueprint


class PublicationSearchForm(SearchForm):
    total = SelectField('Total', choices=[('BRC', 'BRC'), ('Theme', 'Theme'), ('Academic', 'Academic')])
    measure = SelectField('Measure', choices=[('Percentage', 'Percentage'), ('Publications', 'Publications')])
    theme_id = SelectField('Theme')
    nihr_acknowledgement_id = SelectMultipleField('Acknowledgement')
    academic_id = HiddenField()
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
    search_form = PublicationSearchForm(formdata=request.args)

    return render_template("ui/reports/reports.html", search_form=search_form, report_defs=get_report_defs(search_form))


def get_report_defs(search_form):
    report_defs = []

    if search_form.total.data == 'Academic':
        publications = publication_search_query(search_form).alias()

        q = (
            select(distinct(Academic.id).label('academic_id'))
            .select_from(
                publications
            ).join(
                CatalogPublication.catalog_publication_sources
            ).join(
                CatalogPublicationsSources.source
            ).join(
                Source.academic
            )
        )

        for a in db.session.execute(q).mappings().all():
            x = search_form.raw_data_as_dict()
            x['academic_id'] = a['academic_id']
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
    count_dups = ''

    if search_form.has_value('academic_id'):
        a : Academic = Academic.query.get_or_404(search_form.academic_id.data)

        title = f'{a.full_name} Publications by Acknowledgement Status'
        count_dups = ' (NB: publications may be associated with multiple academics)'
    elif search_form.has_value('theme_id') or search_form.total.data == "Theme":
        title = 'Theme Publications by Acknowledgement Status'
        count_dups = ' (NB: publications may be associated with multiple themes)'
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
    
    c = publication_count(search_form)

    bc: BarChart = BarChart(
        title=title,
        items=publication_summary(search_form),
        y_title=y_title,
        x_title=f'Publication Count = {c}{count_dups}'
    )

    if search_form.measure.data == 'Percentage':
        bc.value_formatter = lambda x: f'{x}%'

    return bc.send_as_attachment()


@blueprint.route("/academics/export/csv")
def academics_export_csv():
    headers = {
        'first_name': None,
        'last_name': None,
        'theme': None,
        'ordcid': None,
    }

    q = select(Academic).where(Academic.initialised == True)

    academic_details = ({
        'first_name': a.first_name,
        'last_name': a.last_name,
        'theme': a.theme.name,
        'ordcid': a.orcid,
    } for a in db.session.scalars(q).all())

    return csv_download('Academics', headers.keys(), academic_details)
