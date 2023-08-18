from flask import render_template, request
from lbrc_flask.charting import BarChart, BarChartItem
from lbrc_flask.database import db
from lbrc_flask.forms import SearchForm
from sqlalchemy import distinct, func, select
from sqlalchemy.sql.expression import literal
from wtforms import MonthField, SelectField, HiddenField, SelectMultipleField

from academics.model import (Academic, NihrAcknowledgement, ScopusAuthor,
                             ScopusPublication, Theme)
from academics.publication_searching import publication_search_query, publication_attribution_query

from .. import blueprint

def _get_nihr_acknowledgement_choices():
    return [(f.id, f.name.title()) for f in NihrAcknowledgement.query.order_by(NihrAcknowledgement.name).all()]


class PublicationSearchForm(SearchForm):
    total = SelectField('Total', choices=[('BRC', 'BRC'), ('Theme', 'Theme'), ('Academic', 'Academic')])
    measure = SelectField('Measure', choices=[('Percentage', 'Percentage'), ('Publications', 'Publications')])
    theme_id = SelectField('Theme')
    nihr_acknowledgement_id = SelectMultipleField('Acknowledgement')
    academic_id = HiddenField()
    publication_date_start = MonthField('Publication Start Date')
    publication_date_end = MonthField('Publication End Date')
    supress_validation_historic = HiddenField('supress_validation_historic', default=True)

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
            x = search_form.as_dict()
            x['academic_id'] = a['academic_id']
            report_defs.append(x)
    else:
        report_defs.append(search_form.as_dict())

    return report_defs


@blueprint.route("/reports/image")
def report_image():
    search_form = PublicationSearchForm(formdata=request.args)

    if search_form.has_value('academic_id'):
        a : Academic = Academic.query.get_or_404(search_form.academic_id.data)

        title = f'{a.full_name} Publications by Acknowledgement Status'
        publications = get_publication_by_main_academic(search_form)
    elif search_form.has_value('theme_id'):
        title = 'Theme Publications by Acknowledgement Status'
        publications = get_publication_by_main_theme(search_form)
    elif search_form.total.data == "Theme":
        title = 'Theme Publications by Acknowledgement Status'
        publications = get_publication_by_main_theme(search_form)
    else:
        title = 'BRC Publications by Acknowledgement Status'
        publications = get_publication_by_brc(search_form)

    results = by_acknowledge_status(publications)

    if search_form.measure.data == 'Publications':
        title += " Count"
        items = publication_count_value(results)
        y_title = 'Publications'
        show_total = True
    else:
        title += " Percentage"
        items = percentage_value(results)
        y_title = 'Percentage'
        show_total = False

    bc: BarChart = BarChart(
        title=title,
        items=items,
        y_title=y_title,
        show_total=show_total,
    )

    if search_form.measure.data == 'Percentage':
        bc.value_formatter = lambda x: f'{x}%'

    return bc.send_as_attachment()


def get_publication_by_main_theme(search_form):
    publications = publication_search_query(search_form).alias()
    attribution = publication_attribution_query().alias()

    return select(
        publications.c.id.label('scopus_publication_id'),
        Theme.name.label('bucket')
    ).join(
        attribution, attribution.c.scopus_publication_id == publications.c.id
    ).join(
        Theme, Theme.id == attribution.c.theme_id
    ).alias()


def get_publication_by_main_academic(search_form):
    publications = publication_search_query(search_form).alias()
    attribution = publication_attribution_query().alias()

    return select(
        publications.c.id.label('scopus_publication_id'),
        func.concat(Academic.first_name, Academic.last_name).label('bucket')
    ).join(
        attribution, attribution.c.scopus_publication_id == publications.c.id
    ).join(
        Academic, Academic.id == attribution.c.academic_id
    ).order_by(
        Academic.last_name,
        Academic.first_name,
    ).alias()


def get_publication_by_brc(search_form):
    publications = publication_search_query(search_form).alias()

    return select(
        publications.c.id.label('scopus_publication_id'),
        literal('brc').label('bucket')
    ).alias()


def by_acknowledge_status(publications):
    q_total = (
        select(
            publications.c.bucket,
            func.count().label('total_count'),
        )
        .select_from(publications)
        .group_by(publications.c.bucket)
    ).alias()

    q = (
        select(
            publications.c.bucket,
            func.coalesce(NihrAcknowledgement.name, 'Unvalidated').label('acknowledgement_name'),
            func.count().label('publications'),
            q_total.c.total_count
        )
        .select_from(ScopusPublication)
        .join(publications, publications.c.scopus_publication_id == ScopusPublication.id)
        .join(NihrAcknowledgement, NihrAcknowledgement.id == ScopusPublication.nihr_acknowledgement_id, isouter=True)
        .join(q_total, q_total.c.bucket == publications.c.bucket)
        .group_by(func.coalesce(NihrAcknowledgement.name, 'Unvalidated'), publications.c.bucket)
        .order_by(func.coalesce(NihrAcknowledgement.name, 'Unvalidated'), publications.c.bucket)
    )

    return db.session.execute(q).mappings().all()


def publication_count_value(results):
    return [BarChartItem(
        series=p['acknowledgement_name'],
        bucket=p['bucket'],
        count=p['publications']
    ) for p in results]


def percentage_value(results):
    return [BarChartItem(
        series=p['acknowledgement_name'],
        bucket=p['bucket'],
        count=round(p['publications'] * 100 / p['total_count'])
    ) for p in results]


