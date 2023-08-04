from dateutil.relativedelta import relativedelta
from flask import render_template, request
from lbrc_flask.charting import BarChart, BarChartItem
from lbrc_flask.database import db
from lbrc_flask.forms import SearchForm
from sqlalchemy import func, select
from sqlalchemy.sql.expression import literal
from wtforms import MonthField, SelectField, HiddenField
from lbrc_flask.validators import parse_date_or_none

from academics.model import (Academic, NihrAcknowledgement, ScopusAuthor,
                             ScopusPublication, Theme, Subtype)

from .. import blueprint


class PublicationSearchForm(SearchForm):
    total = SelectField('Total', choices=[('BRC', 'BRC'), ('Theme', 'Theme'), ('Author', 'Author')])
    measure = SelectField('Measure', choices=[('Percentage', 'Percentage'), ('Publications', 'Publications')])
    theme_id = SelectField('Theme')
    academic_id = HiddenField()
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

    return render_template("ui/reports/reports.html", search_form=search_form, report_defs=get_report_defs(search_form))


def get_report_defs(search_form):
    report_defs = []

    date_end = date_start = None

    if search_form.has_value('publication_date_start'):
        date_start = search_form.publication_date_start.data.strftime('%Y-%m')
    if search_form.has_value('publication_date_end'):
        date_end = search_form.publication_date_end.data.strftime('%Y-%m')

    if search_form.total.data == 'Author':
        publication_authors = get_publication_author_query(
            start_date=search_form.publication_date_start.data,
            end_date=search_form.publication_date_end.data,
        )

        q = (
            select(publication_authors.c.academic_id)
            .select_from(publication_authors)
            
            .group_by(publication_authors.c.academic_id)
            .order_by(publication_authors.c.academic_name)
        )

        if search_form.has_value('theme_id'):
            q = q.where(publication_authors.c.theme_id == search_form.theme_id.data)

        for a in db.session.execute(q).mappings().all():
            report_defs.append({
                'academic_id': a['academic_id'],
                'publication_date_start': date_start,
                'publication_date_end': date_end,
                'measure': search_form.measure.data,
                'total': search_form.total.data,
            })
    elif search_form.has_value('theme_id'):
        report_defs.append({
            'theme_id': search_form.theme_id.data,
            'publication_date_start': date_start,
            'publication_date_end': date_end,
            'measure': search_form.measure.data,
            'total': search_form.total.data,
        })
    else:
        report_defs.append({
            'publication_date_start': date_start,
            'publication_date_end': date_end,
            'measure': search_form.measure.data,
            'total': search_form.total.data,
        })
    
    return report_defs


@blueprint.route("/reports/image")
def report_image():
    search_form = get_search_form()

    if search_form.has_value('academic_id'):
        title = 'Author Publications by Acknowledgement Status'
        publications = get_publication_by_main_academic(
            academic_id=search_form.academic_id.data,
            start_date=search_form.publication_date_start.data,
            end_date=search_form.publication_date_end.data,
        )
    elif search_form.has_value('theme_id'):
        title = 'Theme Publications by Acknowledgement Status'
        publications = get_publication_by_main_theme(
            theme_id=search_form.theme_id.data,
            start_date=search_form.publication_date_start.data,
            end_date=search_form.publication_date_end.data,
        )
    elif search_form.total.data == "BRC":
        title = 'BRC Publications by Acknowledgement Status'
        publications = get_publication_by_brc(
            start_date=search_form.publication_date_start.data,
            end_date=search_form.publication_date_end.data,
        )
    else:
        title = 'Theme Publications by Acknowledgement Status'
        publications = get_publication_by_main_theme(
            start_date=search_form.publication_date_start.data,
            end_date=search_form.publication_date_end.data,
        )
    
    results = by_acknowledge_status(publications)

    if search_form.measure.data == 'Publications':
        title += " Count"
        items = publication_count_value(results)
    else:
        title += " Percentage"
        items = percentage_value(results)

    bc: BarChart = BarChart(
        title=title,
        items=items,
    )

    if search_form.measure.data == 'Percentage':
        bc.value_formatter = lambda x: f'{x}%'

    return bc.send_as_attachment()


def get_publication_theme_query(start_date, end_date):
    q = (
        select(
            ScopusPublication.id.label('scopus_publication_id'),
            Theme.id.label('theme_id'),
            Theme.name.label('theme_name'),
            func.row_number().over(partition_by=ScopusPublication.id, order_by=[func.count().desc(), Theme.id]).label('priority')
        )
        .join(ScopusPublication.scopus_authors)
        .join(ScopusAuthor.academic)
        .join(Theme, Theme.id == Academic.theme_id)
        .where(ScopusPublication.subtype_id.in_([s.id for s in Subtype.get_validation_types()]))
        .where(func.coalesce(ScopusPublication.validation_historic, False) == False)
        .group_by(ScopusPublication.id, Theme.id, Theme.name)
        .order_by(ScopusPublication.id, func.count().desc(), Theme.id, Theme.name)
    )

    publication_start_date = parse_date_or_none(start_date)
    if publication_start_date:
        q = q.filter(ScopusPublication.publication_cover_date >= publication_start_date)

    publication_end_date = parse_date_or_none(end_date)
    if publication_end_date:
        q = q.filter(ScopusPublication.publication_cover_date < (publication_end_date + relativedelta(months=1)))

    publication_themes = q.alias()

    return (
        select(
            publication_themes.c.scopus_publication_id,
            publication_themes.c.theme_id,
            publication_themes.c.theme_name,
        )
        .select_from(publication_themes)
        .where(publication_themes.c.priority == 1)
    ).alias()



def get_publication_author_query(start_date, end_date):
    academic_publications = (
        select(
            ScopusAuthor.academic_id,
            ScopusPublication.id.label('scopus_publication_id')
        )
        .join(ScopusPublication.scopus_authors)
    ).alias()
    
    publication_themes = get_publication_theme_query(start_date, end_date)

    q = (
        select(
            publication_themes.c.scopus_publication_id,
            publication_themes.c.theme_id,
            Academic.id.label('academic_id'),
            func.concat(Academic.first_name, ' ', Academic.last_name).label('academic_name'),
            func.row_number().over(partition_by=publication_themes.c.scopus_publication_id, order_by=[func.count().desc(), Academic.id]).label('priority')
        )
        .select_from(publication_themes)
        .join(academic_publications, academic_publications.c.scopus_publication_id == publication_themes.c.scopus_publication_id)
        .join(Academic, Academic.id == academic_publications.c.academic_id)
        .where(Academic.theme_id == publication_themes.c.theme_id)
        .group_by(publication_themes.c.scopus_publication_id, Academic.id, func.concat(Academic.first_name, ' ', Academic.last_name))
        .order_by(publication_themes.c.scopus_publication_id, func.count().desc(), Academic.id, func.concat(Academic.first_name, ' ', Academic.last_name))
    )
 
    publication_authors = q.alias()

    return (
        select(
            publication_authors.c.scopus_publication_id,
            publication_authors.c.theme_id,
            publication_authors.c.academic_id,
            publication_authors.c.academic_name
        )
        .select_from(publication_authors)
        .where(publication_authors.c.priority == 1)
    ).alias()


def get_publication_by_main_theme(start_date, end_date, theme_id=None):
    publication_themes = get_publication_theme_query(start_date, end_date)

    q = (
        select(
            publication_themes.c.scopus_publication_id,
            publication_themes.c.theme_name.label('bucket')
        )
        .select_from(publication_themes)
    )

    if theme_id:
        q = q.where(publication_themes.c.theme_id == theme_id)

    return q.alias()


def get_publication_by_main_academic(academic_id, start_date, end_date):
    q = get_publication_author_query(start_date, end_date)

    return (
        select(
            q.c.scopus_publication_id,
            q.c.academic_name.label('bucket')
        )
        .select_from(q)
        .where(q.c.academic_id == academic_id)
    ).alias()


def get_publication_by_brc(start_date, end_date):
    q = get_publication_author_query(start_date, end_date)

    return (
        select(
            q.c.scopus_publication_id,
            literal('brc').label('bucket')
        )
        .select_from(q)
    ).alias()


def by_acknowledge_status(publications):
    q_count = select(func.count()).select_from(publications)
    total_count = db.session.execute(q_count).scalar()

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
