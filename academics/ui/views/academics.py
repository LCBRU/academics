from flask import flash, render_template, request, redirect, url_for
from lbrc_flask.forms import ConfirmForm, FlashingForm, SearchForm
from lbrc_flask.database import db
from lbrc_flask.response import trigger_response, refresh_response
from sqlalchemy import delete, select, func
from wtforms.fields.simple import HiddenField, StringField, BooleanField
from wtforms import SelectField, SelectMultipleField
from academics.catalogs.jobs import AcademicRefresh, RefreshAll
from academics.catalogs.scopus import scopus_author_search
from academics.catalogs.service import refresh, updating
from academics.model.academic import Academic, AcademicPotentialSource
from academics.model.publication import CATALOG_SCOPUS
from wtforms.validators import Length, DataRequired
from sqlalchemy.orm import selectinload
from flask_security import roles_accepted
from lbrc_flask.async_jobs import AsyncJobs

from academics.model.theme import Theme
from academics.services.academic_searching import AcademicSearchForm, academic_search_query
from academics.services.sources import create_potential_sources, get_sources_for_catalog_identifiers
from .. import blueprint


def _get_academic_choices():
    academics = Academic.query.all()
    academics = sorted(academics, key=lambda a: ' '.join([a.last_name, a.first_name]))

    return [(0, 'New Academic')] + [(a.id, a.full_name) for a in academics]


class AddAuthorSearchForm(SearchForm):
    show_non_local = BooleanField('Show Non-Local', default=False)


class AddAuthorForm(FlashingForm):
    catalog_identifier = HiddenField()


class AddAuthorEditForm(FlashingForm):
    catalog_identifier = HiddenField()
    academic_id = SelectField('Academic', choices=[], default=0)
    themes = SelectField('Theme', coerce=int, default=0, validators=[DataRequired()])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.academic_id.choices = _get_academic_choices()
        self.themes.choices = [(0, '')] + [(t.id, t.name) for t in Theme.query.all()]


class AcademicEditForm(FlashingForm):
    first_name = StringField("First Name", validators=[Length(max=500)])
    last_name = StringField("Last Name", validators=[Length(max=500)])
    initials = StringField("Initials", validators=[Length(max=255)])
    google_scholar_id = StringField("Google Scholar ID", validators=[Length(max=255)])
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
        "ui/academic/index.html",
        academics=academics,
        search_form=search_form,
        confirm_form=ConfirmForm(),
        updating=updating(),
    )


@blueprint.route("/academic/<int:id>/edit", methods=['GET', 'POST'])
@roles_accepted('editor')
def academic_edit(id):
    academic = db.get_or_404(Academic, id)

    form = AcademicEditForm(data={
        'first_name': academic.first_name,
        'last_name': academic.last_name,
        'initials': academic.initials,
        'google_scholar_id': academic.google_scholar_id,
        'orcid': academic.orcid,
        'has_left_brc': academic.has_left_brc,
        'themes': [t.id for t in academic.themes]
    })

    if form.validate_on_submit():
        academic.first_name = form.first_name.data
        academic.last_name = form.last_name.data
        academic.initials = form.initials.data
        academic.google_scholar_id = form.google_scholar_id.data
        academic.orcid = form.orcid.data
        academic.themes = [db.session.get(Theme, t) for t in form.themes.data]
        academic.has_left_brc = form.has_left_brc.data

        db.session.add(academic)
        db.session.commit()

        return refresh_response()

    return render_template(
        "lbrc/form_modal.html",
        title=f"Edit Academic {academic.full_name}",
        form=form,
        url=url_for('ui.academic_edit', id=id),
    )


@blueprint.route("/update_all_academics")
@roles_accepted('admin')
def update_all_academics():
    AsyncJobs.schedule(RefreshAll())

    return redirect(url_for('ui.index'))


@blueprint.route("/trigger_refresh")
@roles_accepted('admin')
def trigger_refresh():
    refresh()

    return redirect(url_for('ui.index'))


@blueprint.route("/add_author_search")
@roles_accepted('editor')
def add_author_search():
    search_form = AddAuthorSearchForm(formdata=request.args)

    authors = []

    try:
        if search_form.search.data:
            authors = scopus_author_search(
                search_string=search_form.search.data,
                search_non_local=search_form.show_non_local.data,
            )
    except:
        flash('Search failed.  Please tighten your search criteria.')

    return render_template(
        "ui/academic/add_search.html",
        authors=authors,
        academics=sorted(Academic.query.all(), key=lambda a: a.last_name + a.first_name),
        search_form=search_form,
        add_author_form=AddAuthorForm(),
    )


@blueprint.route("/add_author_search_results")
@roles_accepted('editor')
def add_author_search_results():
    search_form = AddAuthorSearchForm(formdata=request.args)

    authors = []

    try:
        authors = scopus_author_search(
            search_string=search_form.search.data,
            search_non_local=search_form.show_non_local.data,
        )
    except Exception as e:
        print(e)
        flash('Search failed.  Please tighten your search criteria.')

    return render_template(
        "ui/academic/add_search_results.html",
        authors=authors,
        search_form=search_form,
        add_form=AddAuthorForm(),
    )


@blueprint.route("/add_author", methods=['GET'])
@roles_accepted('editor')
def add_author():
    form = AddAuthorEditForm()

    return render_template(
        "ui/academic/add_author.html",
        form=form,
    )


@blueprint.route("/add_author", methods=['POST'])
@roles_accepted('editor')
def add_author_submit():
    form = AddAuthorEditForm()

    if form.validate_on_submit():
        if form.academic_id.data:
            academic = db.session.get(Academic, form.academic_id.data)

        if not academic:
            academic = Academic()
            academic.themes = [db.session.get(Theme, form.themes.data)]
            db.session.add(academic)
        
        sources = get_sources_for_catalog_identifiers(CATALOG_SCOPUS, request.form.getlist('catalog_identifier'))
        create_potential_sources(sources, academic, not_match=False)
        db.session.commit()

        AsyncJobs.schedule(AcademicRefresh(academic))

        return trigger_response('refreshSearch')
    
    return render_template(
        "ui/academic/add_author.html",
        form=form,
    )


@blueprint.route("/delete_academic/<int:id>", methods=['POST'])
@roles_accepted('editor')
def delete_academic(id):
    a = db.get_or_404(Academic, id)

    db.session.execute(
        delete(AcademicPotentialSource)
        .where(AcademicPotentialSource.academic_id == a.id)
    )

    db.session.delete(a)
    db.session.commit()

    return refresh_response()


@blueprint.route("/update_academic/<int:id>", methods=['POST'])
@roles_accepted('editor')
def update_academic(id):
    academic = db.get_or_404(Academic, id)

    AsyncJobs.schedule(AcademicRefresh(academic))

    return refresh_response()


@blueprint.route("/is_updating")
def is_updating():
    q = select(func.count(Academic.id)).where(Academic.updating == True)
    return render_template("ui/updating.html", count=db.session.execute(q).scalar())
