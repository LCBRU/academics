from datetime import date, datetime
from random import randint
from tempfile import NamedTemporaryFile

from flask import render_template, request, send_file
from lbrc_flask.charting import grouped_bar_chart, BarChart, BarChartItem
from lbrc_flask.forms import SearchForm
from wtforms import MonthField, SelectField

from academics.model import Theme
from academics.ui.views.publications import _get_publication_query

from .. import blueprint


class PublicationSearchForm(SearchForm):
    theme_id = SelectField('Theme')
    publication_date_start = MonthField('Publication Start Date')
    publication_date_end = MonthField('Publication End Date')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.theme_id.choices = [('', '')] + [(t.id, t.name) for t in Theme.query.all()]


def get_search_form():
    if request.args:
        return PublicationSearchForm(formdata=request.args)
    else:
        return PublicationSearchForm()


@blueprint.route("/reports", methods=['GET', 'POST'])
def reports():
    search_form = get_search_form()

    return render_template("ui/reports/reports.html", search_form=search_form)


@blueprint.route("/reports/image")
def report_image():
    search_form = get_search_form()

    items = [BarChartItem(
        series='BRC',
        bucket=p.theme,
    ) for p in _get_publication_query(search_form)]

    bc: BarChart = BarChart(
        title='Temp Name',
        items=items,
    )

    return bc.send_as_attachment()
