from flask import render_template, request
from lbrc_flask.charting import BarChart
from lbrc_flask.database import db
from sqlalchemy import distinct, select
from lbrc_flask.export import csv_download
from sqlalchemy import select
from academics.model.academic import Academic
from academics.services.academic_searching import academic_search_query
from academics.services.publication_searching import PublicationSummarySearchForm, publication_count, publication_summary

from .. import blueprint


@blueprint.route("/reports", methods=['GET', 'POST'])
def reports():
    search_form = PublicationSummarySearchForm(formdata=request.args)

    return render_template("ui/reports/reports.html", search_form=search_form, report_defs=get_report_defs(search_form))


def get_report_defs(search_form):
    report_defs = []

    if search_form.summary_type == search_form.SUMMARY_TYPE__ACADEMIC:
        q = academic_search_query(search_form).with_only_columns(Academic.id)

        for academic_id in db.session.execute(q).scalars():
            x = search_form.raw_data_as_dict()
            x['academic_id'] = academic_id
            x['supress_validation_historic'] = search_form.supress_validation_historic.data
            report_defs.append(x)
    else:
        x = search_form.raw_data_as_dict()
        x['supress_validation_historic'] = search_form.supress_validation_historic.data
        report_defs.append(x)

    return report_defs


@blueprint.route("/reports/image")
def report_image():
    search_form = PublicationSummarySearchForm(formdata=request.args)

    if search_form.summary_type == search_form.SUMMARY_TYPE__ACADEMIC:
        a : Academic = Academic.query.get_or_404(search_form.academic_id.data)
        type_title = a.full_name
    elif search_form.summary_type == search_form.SUMMARY_TYPE__THEME:
        type_title = 'Theme'
    else:
        type_title = 'BRC'

    type_duplicate_message = {
        search_form.SUMMARY_TYPE__ACADEMIC: '(NB: publications may be associated with multiple academics)',
        search_form.SUMMARY_TYPE__THEME: '(NB: publications may be associated with multiple themes)',
        search_form.SUMMARY_TYPE__BRC: None,
    }

    group_by_title = {
        'total': None,
        'acknowledgement': 'by Acknowledgement Status',
        'industry_collaboration': 'by Industrial Collaboration',
    }

    measure_title = {
        'publications': 'Count',
        'percentage': 'Publications',
    }

    measure_y_title = {
        'publications': 'Publications',
        'percentage': 'Publications',
    }

    c = publication_count(search_form)

    bc: BarChart = BarChart(
        title= ' '.join(filter(None, [type_title, 'Publications', group_by_title[search_form.group_by.data], measure_title[search_form.measure.data]])),
        items=publication_summary(search_form),
        y_title=measure_y_title[search_form.measure.data],
        x_title=f'Publication Count = {c}{type_duplicate_message[search_form.summary_type]}'
    )

    if search_form.measure.data == 'Percentage':
        bc.value_formatter = lambda x: f'{x}%'

    return bc.send()


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
