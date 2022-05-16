from datetime import datetime
from flask import render_template, request
from lbrc_flask.forms import SearchForm
from academics.model import ScopusAuthor, ScopusPublication
from .. import blueprint
from sqlalchemy import or_
from wtforms import SelectField


def _get_period_choices():
    return [('', '')] + [(a.id, f'{a.full_name} ({a.affiliation_name})') for a in ScopusAuthor.query.order_by(ScopusAuthor.last_name, ScopusAuthor.first_name).all()]


def _get_author_choices():
    return [('', '')] + [(a.id, f'{a.full_name} ({a.affiliation_name})') for a in ScopusAuthor.query.order_by(ScopusAuthor.last_name, ScopusAuthor.first_name).all()]


class TrackerSearchForm(SearchForm):
    author_id = SelectField('Author', choices=[])
    publication_period = SelectField('Publication Period', choices=[])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.author_id.choices = _get_author_choices()

        this_year = datetime.now().year
        self.publication_period.choices = [(y, y) for y in range(this_year, this_year - 20, -1)]


@blueprint.route("/publications/")
def publications():
    search_form = TrackerSearchForm(formdata=request.args)
    
    q = ScopusPublication.query

    scopus_author = None

    if search_form.author_id.data:
        q = q.filter(ScopusPublication.scopus_authors.any(ScopusAuthor.id == search_form.author_id.data))

    if search_form.search.data:
        q = q.filter(or_(
            ScopusPublication.title.like(f'%{search_form.search.data}%'),
            ScopusPublication.publication.like(f'%{search_form.search.data}%'),
        ))
    q = q.order_by(ScopusPublication.publication_cover_date.desc())

    publications = q.paginate(
        page=search_form.page.data,
        per_page=5,
        error_out=False,
    )

    return render_template(
        "ui/publications.html",
        search_form=search_form,
        scopus_author=scopus_author,
        publications=publications,
    )
