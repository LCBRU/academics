from flask import render_template, request
from lbrc_flask.charting import BarChart, BarChartItem
from lbrc_flask.database import db
from lbrc_flask.forms import SearchForm
from sqlalchemy import func, select
from wtforms import MonthField, SelectField, HiddenField

from academics.model import (Academic, NihrAcknowledgement, ScopusAuthor,
                             ScopusPublication, Theme, Subtype)

from .. import blueprint


class PublicationSearchForm(SearchForm):
    total = SelectField('Total', choices=[('Theme', 'Theme'), ('Author', 'Author')])
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

    print(search_form.data)

    return render_template("ui/reports/reports.html", search_form=search_form, report_defs=get_report_defs(search_form))


def get_report_defs(search_form):
    report_defs = []

    if search_form.total.data == 'Author':

        publication_authors = get_publication_author_query()

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
                'publication_date_start': search_form.publication_date_start.data,
                'publication_date_end': search_form.publication_date_end.data,
            })
    elif search_form.has_value('theme_id'):
        report_defs.append({
            'theme_id': search_form.theme_id.data,
            'publication_date_start': search_form.publication_date_start.data,
            'publication_date_end': search_form.publication_date_end.data,
        })
    else:
        report_defs.append({
            'publication_date_start': search_form.publication_date_start.data,
            'publication_date_end': search_form.publication_date_end.data,
        })
    
    return report_defs


@blueprint.route("/reports/image")
def report_image():
    search_form = get_search_form()

    if search_form.has_value('academic_id'):
        title = 'Author Publications by Acknowledgement Status'
        publications = get_publication_by_main_academic(search_form.academic_id.data)
    elif search_form.has_value('theme_id'):
        title = 'Theme Publications by Acknowledgement Status'
        publications = get_publication_by_main_theme(search_form.theme_id.data)
    else:
        title = 'Theme Publications by Acknowledgement Status'
        publications = get_publication_by_main_theme()
    
    items = by_acknowledge_status(publications) 

    bc: BarChart = BarChart(
        title=title,
        items=items,
    )

    return bc.send_as_attachment()


def get_publication_theme_query():
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



def get_publication_author_query():
    academic_publications = (
        select(
            ScopusAuthor.academic_id,
            ScopusPublication.id.label('scopus_publication_id')
        )
        .join(ScopusPublication.scopus_authors)
    ).alias()
    
    publication_themes = get_publication_theme_query()

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


def get_publication_by_main_theme(theme_id=None):
    q = get_publication_theme_query()

    if theme_id:
        q = q.where(q.c.theme_id == theme_id)

    return (
        select(
            q.c.scopus_publication_id,
            q.c.theme_name.label('bucket')
        )
        .select_from(q)
    ).alias()


def get_publication_by_main_academic(academic_id):
    q = get_publication_author_query()

    return (
        select(
            q.c.scopus_publication_id,
            q.c.academic_name.label('bucket')
        )
        .select_from(q)
        .where(q.c.academic_id == academic_id)
    ).alias()


def by_acknowledge_status(publications):
    q = (
        select(
            publications.c.bucket,
            func.coalesce(NihrAcknowledgement.name, 'Unvalidated').label('acknowledgement_name'),
            func.count().label('publications'),
        )
        .select_from(ScopusPublication)
        .join(publications, publications.c.scopus_publication_id == ScopusPublication.id)
        .join(NihrAcknowledgement, NihrAcknowledgement.id == ScopusPublication.nihr_acknowledgement_id, isouter=True)
        .group_by(func.coalesce(NihrAcknowledgement.name, 'Unvalidated'), publications.c.bucket)
        .order_by(func.coalesce(NihrAcknowledgement.name, 'Unvalidated'), publications.c.bucket)
    )

    results = db.session.execute(q).mappings().all()

    return [BarChartItem(
        series=p['acknowledgement_name'],
        bucket=p['bucket'],
        count=p['publications']
    ) for p in results]
