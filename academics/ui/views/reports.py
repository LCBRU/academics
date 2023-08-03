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
    subtype_id = HiddenField()
    theme_id = SelectField('Theme')
    publication_date_start = MonthField('Publication Start Date')
    publication_date_end = MonthField('Publication End Date')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.subtype_id.data = [s.id for s in Subtype.get_validation_types()]
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

    

    q = (ScopusPublication.query
        .with_entities(
            ScopusPublication.id,
            func.row_number().over(partition_by=ScopusPublication.id)
        )
    )

    publication_themes = (
        select(
            ScopusPublication.id.label('scopus_publication_id'),
            Academic.theme_id,
            func.row_number().over(partition_by=ScopusPublication.id).label('priority')
        ).join(ScopusPublication.scopus_authors)
        .join(ScopusAuthor.academic)
        .group_by(ScopusPublication.id, Academic.theme_id)
        .order_by(ScopusPublication.id, Academic.theme_id, func.count().desc())
    ).alias()

    publication_theme = (
        select(
            publication_themes.c.scopus_publication_id,
            publication_themes.c.theme_id
        )
        .select_from(publication_themes)
        .where(publication_themes.c.priority == 1)
    ).alias()

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

    print(q)

    results = db.session.execute(q).mappings().all()

    items = [BarChartItem(
        series=p['acknowledgement_name'],
        bucket=p['theme_name'],
        count=p['publications']
    ) for p in results]

    bc: BarChart = BarChart(
        title='Theme publications by acknowledgement status',
        items=items,
    )

    return bc.send_as_attachment()
