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

    return render_template("ui/reports/reports.html", search_form=search_form)


@blueprint.route("/reports/image")
def report_image():
    search_form = get_search_form()

    bc: BarChart = BarChart(
        title='Theme publications by acknowledgement status',
        items=items(search_form),
    )

    return bc.send_as_attachment()


def items(search_form):
    publication_theme = get_publication_themes(search_form)

    return theme_statuses(publication_theme)


def get_publication_themes(search_form):
    q = (
        select(
            ScopusPublication.id.label('scopus_publication_id'),
            Academic.theme_id,
            func.row_number().over(partition_by=ScopusPublication.id).label('priority')
        ).join(ScopusPublication.scopus_authors)
        .join(ScopusAuthor.academic)
        .where(ScopusPublication.subtype_id.in_([s.id for s in Subtype.get_validation_types()]))
        .group_by(ScopusPublication.id, Academic.theme_id)
        .order_by(ScopusPublication.id, Academic.theme_id, func.count().desc())
    )

    if search_form.has_value('theme_id'):
        q = q.where(Academic.theme_id == search_form.theme_id.data)

    publication_themes = q.alias()

    return (
        select(
            publication_themes.c.scopus_publication_id,
            publication_themes.c.theme_id
        )
        .select_from(publication_themes)
        .where(publication_themes.c.priority == 1)
    ).alias()


def theme_statuses(publication_theme):
    q = (
        select(
            Theme.name.label('theme_name'),
            func.coalesce(NihrAcknowledgement.name, 'Unvalidated').label('acknowledgement_name'),
            func.count().label('publications'),
        )
        .join_from(
            ScopusPublication,
            publication_theme,
            publication_theme.c.scopus_publication_id == ScopusPublication.id
        )
        .join(Theme, Theme.id == publication_theme.c.theme_id)
        .join(NihrAcknowledgement, NihrAcknowledgement.id == ScopusPublication.nihr_acknowledgement_id, isouter=True)
        .where(func.coalesce(ScopusPublication.validation_historic, False) == False)
        .group_by(NihrAcknowledgement.name, Theme.name)
        .order_by(NihrAcknowledgement.name, Theme.name)
    )

    results = db.session.execute(q).mappings().all()

    return [BarChartItem(
        series=p['acknowledgement_name'],
        bucket=p['theme_name'],
        count=p['publications']
    ) for p in results]
