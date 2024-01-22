from flask import render_template, request, redirect, url_for
from lbrc_flask.forms import ConfirmForm, FlashingForm, SearchForm
from lbrc_flask.database import db
from sqlalchemy import delete
from wtforms.fields.simple import HiddenField, StringField, BooleanField
from wtforms import SelectField, SelectMultipleField
from academics.catalogs.scopus import scopus_author_search
from academics.catalogs.service import add_sources_to_academic, refresh, update_academics, update_single_academic, updating
from academics.model.academic import Academic, AcademicPotentialSource
from academics.model.publication import CATALOG_SCOPUS
from wtforms.validators import Length
from sqlalchemy.orm import selectinload

from academics.model.theme import Theme
from academics.services.academic_searching import AcademicSearchForm, academic_search_query
from .. import blueprint


def _get_academic_choices():
    academics = Academic.query.all()
    academics = sorted(academics, key=lambda a: ' '.join([a.last_name, a.first_name]))

    return [(0, 'New Academic')] + [(a.id, a.full_name) for a in academics]


class AddAuthorForm(FlashingForm):
    catalog_identifier = HiddenField()
    academic_id = SelectField('Academic', choices=[], default=0)
    themes = SelectField('Theme', coerce=int)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.academic_id.choices = _get_academic_choices()
        self.themes.choices = [(t.id, t.name) for t in Theme.query.all()]


class AcademicEditForm(FlashingForm):
    first_name = StringField("First Name", validators=[Length(max=500)])
    last_name = StringField("Last Name", validators=[Length(max=500)])
    orcid = StringField("ORCID", validators=[Length(max=255)])
    themes = SelectMultipleField('Theme', coerce=int)
    has_left_brc = BooleanField('Has Left BRC', default=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.themes.choices = [(t.id, t.name) for t in Theme.query.all()]


@blueprint.route("/")
def index():
    search_form = AcademicSearchForm(formdata=request.args)

    q = academic_search_query(search_form)
    q = q.options(selectinload(Academic.sources))

    academics = db.paginate(
        select=q,
        page=search_form.page.data,
        per_page=5,
        error_out=False,
    )

    return render_template(
        "ui/index.html",
        academics=academics,
        search_form=search_form,
        confirm_form=ConfirmForm(),
        updating=updating(),
    )


@blueprint.route("/academic/<int:id>/edit", methods=['GET', 'POST'])
def academic_edit(id):
    academic = db.get_or_404(Academic, id)

    form = AcademicEditForm(data={
        'first_name': academic.first_name,
        'last_name': academic.last_name,
        'orcid': academic.orcid,
        'has_left_brc': academic.has_left_brc,
        'themes': [t.id for t in academic.themes]
    })

    if form.validate_on_submit():
        academic.first_name = form.first_name.data
        academic.last_name = form.last_name.data
        academic.orcid = form.orcid.data
        academic.themes = [db.session.get(Theme, t) for t in form.themes.data]
        academic.has_left_brc = form.has_left_brc.data

        db.session.add(academic)
        db.session.commit()

        return redirect(url_for('ui.index'))

    return render_template("ui/academic_edit.html", form=form, academic=academic)


@blueprint.route("/update_all_academics")
def update_all_academics():
    if not updating():
        update_academics()

    return redirect(url_for('ui.index'))


@blueprint.route("/trigger_refresh")
def trigger_refresh():
    if not updating():
        refresh()

    return redirect(url_for('ui.index'))


@blueprint.route("/add_author_search")
def add_author_search():
    search_form = SearchForm(formdata=request.args)

    authors = []

    if search_form.search.data:
        authors = scopus_author_search(search_form.search.data)

    return render_template(
        "ui/add_author_search.html",
        authors=authors,
        academics=sorted(Academic.query.all(), key=lambda a: a.last_name + a.first_name),
        search_form=search_form,
        add_author_form=AddAuthorForm(),
    )


@blueprint.route("/add_author", methods=['POST'])
def add_author():
    form = AddAuthorForm()

    add_sources_to_academic(
        catalog=CATALOG_SCOPUS,
        catalog_identifiers=request.form.getlist('catalog_identifier'),
        academic_id=form.academic_id.data,
        themes=[db.session.get(Theme, form.themes.data)],
    )

    return redirect(url_for('ui.index'))


@blueprint.route("/delete_academic", methods=['POST'])
def delete_academic():
    form = ConfirmForm()

    if form.validate_on_submit():
        a = db.get_or_404(Academic, form.id.data)

        db.session.execute(
            delete(AcademicPotentialSource)
            .where(AcademicPotentialSource.academic_id == a.id)
        )

        db.session.delete(a)
        db.session.commit()

    return redirect(url_for('ui.index'))


@blueprint.route("/update_academic", methods=['POST'])
def update_academic():
    form = ConfirmForm()

    if form.validate_on_submit():
        academic = db.get_or_404(Academic, form.id.data)

        update_single_academic(academic)

    return redirect(url_for('ui.index'))
