from flask import render_template, request
from lbrc_flask.charting import BarChart, SeriesConfig, default_series_colors
from lbrc_flask.database import db
from sqlalchemy import select
from lbrc_flask.export import csv_download
from sqlalchemy import select
from academics.model.academic import Academic
from academics.model.theme import Theme
from academics.services.academic_searching import academic_search_query, theme_search_query
from academics.services.publication_searching import PublicationSearchForm, PublicationSummarySearchForm, publication_count, publication_search_query, publication_summary, all_series_configs
from lbrc_flask.export import pdf_download

from .. import blueprint


@blueprint.route("/reports", methods=['GET', 'POST'])
def reports():
    search_form = PublicationSummarySearchForm(formdata=request.args)

    return render_template("ui/reports/reports.html", search_form=search_form, report_defs=get_report_defs(search_form))


def get_report_defs(search_form):
    report_defs = []

    if search_form.summary_type == search_form.SUMMARY_TYPE__ACADEMIC:
        q = academic_search_query(search_form).with_only_columns(Academic.id)

        for theme_id in db.session.execute(q).scalars():
            x = search_form.values_as_dict()
            x['academic_id'] = theme_id
            report_defs.append(x)
    elif search_form.summary_type == search_form.SUMMARY_TYPE__THEME:
        q = theme_search_query(search_form).with_only_columns(Theme.id)

        for theme_id in db.session.execute(q).scalars():
            x = search_form.values_as_dict()
            x['theme_id'] = theme_id
            report_defs.append(x)
    else:
        x = search_form.values_as_dict()
        report_defs.append(x)

    return report_defs


@blueprint.route("/reports/image")
@blueprint.route("/reports/image/<string:type>")
def report_image(type='png'):
    search_form = PublicationSummarySearchForm(formdata=request.args)

    if search_form.summary_type == search_form.SUMMARY_TYPE__ACADEMIC:
        a : Academic = Academic.query.get_or_404(search_form.academic_id.data)
        type_title = a.full_name
    elif search_form.summary_type == search_form.SUMMARY_TYPE__THEME:
        t : Theme = Theme.query.get_or_404(search_form.theme_id.data)
        type_title = t.name
    else:
        type_title = 'BRC'

    type_duplicate_message = {
        search_form.SUMMARY_TYPE__ACADEMIC: '(NB: publications may be associated with multiple academics)',
        search_form.SUMMARY_TYPE__THEME: '(NB: publications may be associated with multiple themes)',
        search_form.SUMMARY_TYPE__BRC: '',
    }

    group_by_title = {
        'total': None,
        'acknowledgement': 'by Acknowledgement Status',
        'external_collaboration': 'by External Collaboration',
        'industry_collaboration': 'by Industrial Collaboration',
        'international_collaboration': 'by International Collaboration',
        'theme_collaboration': 'by Theme Collaboration',
        'catalog': 'by Catalog',
    }

    c = publication_count(search_form)

    items = publication_summary(search_form)
    series_config = all_series_configs(search_form)

    bc: BarChart = BarChart(
        title= ' '.join(filter(None, [type_title, 'Publications', group_by_title[search_form.group_by.data]])),
        items=items,
        y_title='Publications',
        x_title=f'Publication Count = {c}{type_duplicate_message[search_form.summary_type]}',
        no_data_text='No publications found',
        show_y_guides=False,
        show_y_labels=False,
        legend_at_bottom_columns=1,
        tooltip_border_radius=10,
        series_config=series_config,
    )

    bc.value_formatter = lambda x: f'{x} ({round(x * 100/c)}%)'

    if type == 'svg':
        return bc.send_svg()
    elif type == 'attachment':
        return bc.send_as_attachment()
    else:
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


@blueprint.route("/reports/pdf")
def reports_pdf():
    search_form = PublicationSearchForm(formdata=request.args)
    
    q = publication_search_query(search_form)

    publications = db.session.execute(q).unique().scalars()

    return pdf_download(
        'ui/reports/pdf.html',
        title='Academics Publications',
        publications=publications,
        parameters=search_form.values_as_dict(),
    )


