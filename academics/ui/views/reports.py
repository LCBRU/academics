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

    print(search_form.data)

    return render_template("ui/reports/reports.html", search_form=search_form, report_defs=get_report_defs(search_form))


def get_report_defs(search_form):
    report_defs = []

    if search_form.has_value('theme_id'):
        for a in Academic.query.filter(Academic.theme_id == search_form.theme_id.data).all():
            report_defs.append({
                'theme_id': search_form.theme_id.data,
                'academic_id': a.id,
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

    bc: BarChart = BarChart(
        title='Theme publications by acknowledgement status',
        items=items(search_form),
    )

    return bc.send_as_attachment()


def items(search_form):

    if search_form.has_value('theme_id'):
        publications = get_publication_by_main_academic(search_form.theme_id.data, search_form.academic_id.data)
    else:
        publications = get_publication_by_main_theme()


    return theme_statuses(publications)


def get_publication_by_main_theme():
    q = (
        select(
            ScopusPublication.id.label('scopus_publication_id'),
            Theme.name.label('bucket'),
            func.row_number().over(partition_by=ScopusPublication.id).label('priority')
        )
        .join(ScopusPublication.scopus_authors)
        .join(ScopusAuthor.academic)
        .join(Theme, Theme.id == Academic.theme_id)
        .where(ScopusPublication.subtype_id.in_([s.id for s in Subtype.get_validation_types()]))
        .where(func.coalesce(ScopusPublication.validation_historic, False) == False)
        .group_by(ScopusPublication.id, Theme.name)
        .order_by(ScopusPublication.id, Theme.name, func.count().desc())
    )

    publication_themes = q.alias()

    return (
        select(
            publication_themes.c.scopus_publication_id,
            publication_themes.c.bucket
        )
        .select_from(publication_themes)
        .where(publication_themes.c.priority == 1)
    ).alias()


def get_publication_by_main_academic(theme_id, academic_id):
    academic_publications = (
        select(
            ScopusAuthor.academic_id,
            ScopusPublication.id.label('scopus_publication_id')
        )
        .join(ScopusPublication.scopus_authors)
    ).alias()

    q = (
        select(
            ScopusPublication.id.label('scopus_publication_id'),
            func.concat(Academic.first_name, ' ', Academic.last_name).label('bucket'),
            func.row_number().over(partition_by=ScopusPublication.id).label('priority')
        )
        .join(ScopusPublication.scopus_authors)
        .join(ScopusAuthor.academic)
        .join(academic_publications, academic_publications.c.academic_id == Academic.id) 
        .where(ScopusPublication.subtype_id.in_([s.id for s in Subtype.get_validation_types()]))
        .where(func.coalesce(ScopusPublication.validation_historic, False) == False)
        .where(Academic.theme_id == theme_id)
        .where(Academic.id == academic_id)
        .group_by(ScopusPublication.id, func.concat(Academic.first_name, ' ', Academic.last_name))
        .order_by(ScopusPublication.id, func.concat(Academic.first_name, ' ', Academic.last_name), func.count().desc())
    )

    publication_themes = q.alias()

    return (
        select(
            publication_themes.c.scopus_publication_id,1
            publication_themes.c.bucket
        )
        .select_from(publication_themes)
        .where(publication_themes.c.priority == 1)
    ).alias()


def theme_statuses(publications):
    q = (
        select(
            publications.c.bucket,
            func.coalesce(NihrAcknowledgement.name, 'Unvalidated').label('acknowledgement_name'),
            func.count().label('publications'),
        )
        .join_from(
            ScopusPublication,
            publications,
            publications.c.scopus_publication_id == ScopusPublication.id
        )
        .join(NihrAcknowledgement, NihrAcknowledgement.id == ScopusPublication.nihr_acknowledgement_id, isouter=True)
        .group_by(NihrAcknowledgement.name, publications.c.bucket)
        .order_by(NihrAcknowledgement.name, publications.c.bucket)
    )

    results = db.session.execute(q).mappings().all()

    return [BarChartItem(
        series=p['acknowledgement_name'],
        bucket=p['bucket'],
        count=p['publications']
    ) for p in results]
