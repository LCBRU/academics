from flask import flash, render_template, request, url_for
from lbrc_flask.forms import ConfirmForm, FlashingForm, SearchForm
from lbrc_flask.database import db
from lbrc_flask.response import trigger_response, refresh_response
from sqlalchemy import delete, select
from wtforms.fields.simple import HiddenField, StringField, BooleanField
from wtforms import DateField, RadioField, SelectField
from academics.jobs.catalogs import AcademicInitialise, AcademicRefresh
from academics.catalogs.scopus import scopus_author_search
from academics.model.academic import Academic, AcademicPotentialSource
from academics.model.publication import CATALOG_SCOPUS
from wtforms.validators import Length, DataRequired, Optional
from sqlalchemy.orm import selectinload
from flask_security import roles_accepted
from lbrc_flask.async_jobs import AsyncJobs, run_jobs_asynch
from lbrc_flask.requests import get_value_from_all_arguments
from functools import partial
from academics.model.security import User, UserPicker
from academics.model.theme import Theme
from academics.services.academic_searching import AcademicSearchForm, academic_search_query
from academics.services.sources import create_potential_sources, get_sources_for_catalog_identifiers
from academics.ui.views.users import render_user_search_add, user_search_query
from lbrc_flask.forms import MultiCheckboxField
from .. import blueprint


def _get_academic_choices():
    academics = db.session.execute(
        select(Academic)
        .where(Academic.initialised == True)
        .order_by(Academic.last_name, Academic.first_name)
    ).scalars()
    return [(0, 'New Academic')] + [(a.id, a.full_name) for a in academics]


class AddAuthorSearchForm(SearchForm):
    show_non_local = BooleanField('Show Non-Local', default=False)


class AddAuthorForm(FlashingForm):
    catalog_identifier = HiddenField()


class AddAuthorEditForm(FlashingForm):
    catalog_identifier = HiddenField()
    academic_id = SelectField('Academic', choices=[], default=0)
    themes = RadioField('Theme', coerce=int, validators=[DataRequired()])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.academic_id.choices = _get_academic_choices()
        self.themes.choices = [(t.id, t.name) for t in Theme.query.all()]


class AcademicEditForm(FlashingForm):
    first_name = StringField("First Name", validators=[Length(max=500), DataRequired()])
    last_name = StringField("Last Name", validators=[Length(max=500), DataRequired()])
    initials = StringField("Initials", validators=[Length(max=255)])
    google_scholar_id = StringField("Google Scholar ID", validators=[Length(max=255)])
    orcid = StringField("ORCID", validators=[Length(max=255)])
    themes = MultiCheckboxField('Theme', coerce=int)
    user_id = SelectField('User', coerce=int, render_kw={'class':' select2'})
    has_left_brc = BooleanField('Has Left BRC', default=False)
    left_brc_date = DateField('Date left BRC', validators=[Optional()])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.themes.choices = [(t.id, t.name) for t in Theme.query.all()]
        users = db.session.execute(user_search_query({
            'search': get_value_from_all_arguments('search_string') or '',
        })).scalars()
        self.user_id.choices = [(0, '[Not a User]')] + [(u.id, u.full_name) for u in users]


@blueprint.route("/")
def index():
    search_form = AcademicSearchForm(formdata=request.args)

    q = academic_search_query(search_form.data)
    q = q.options(selectinload(Academic.sources))

    academics = db.paginate(select=q)

    return render_template(
        "ui/academic/index.html",
        academics=academics,
        search_form=search_form,
        confirm_form=ConfirmForm(),
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
        'left_brc_date': academic.left_brc_date,
        'themes': [t.id for t in academic.themes],
        "user_id": str(academic.user_id),
    })

    if form.validate_on_submit():
        academic.first_name = form.first_name.data
        academic.last_name = form.last_name.data
        academic.initials = form.initials.data
        academic.google_scholar_id = form.google_scholar_id.data
        academic.orcid = form.orcid.data
        academic.themes = [db.session.get(Theme, t) for t in form.themes.data]
        academic.has_left_brc = form.has_left_brc.data
        academic.left_brc_date = form.left_brc_date.data

        user = db.session.execute(
            select(User)
            .where(User.id == form.user_id.data)
            ).scalar_one_or_none()
        
        academic.user = user

        db.session.add(academic)
        db.session.commit()

        return refresh_response()

    return render_template(
        "lbrc/form_modal.html",
        title=f"Edit Academic {academic.full_name}",
        form=form,
        url=url_for('ui.academic_edit', id=id),
    )


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
    form = AddAuthorEditForm(formdata=request.args)

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
        for s in sources:
            s.academic = academic

        AsyncJobs.schedule(AcademicInitialise(academic))
        db.session.commit()

        run_jobs_asynch()

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
    db.session.commit()
    run_jobs_asynch()

    return refresh_response()


@blueprint.route("/is_updating")
def is_updating():
    return render_template("ui/updating.html", count=AsyncJobs.due_count())


@blueprint.route("/academic/<int:academic_id>/user/search")
@roles_accepted('editor')
def academic_user_search(academic_id):
    a: Academic = db.get_or_404(Academic, academic_id)

    return render_template(
        "lbrc/search.html",
        title=f"Assign user to '{a.full_name}'",
        results_url=url_for('ui.academic_user_search_results', academic_id=a.id),
    )


class AcademicUserPicker(UserPicker):
    @property
    def info(self):
        if self.academic:
            return f"Linked to academic {self.academic.full_name}"

    @property
    def not_selectable(self):
        return self.academic


@blueprint.route("/academic/<int:academic_id>/user/search_results/<int:page>")
@blueprint.route("/academic/<int:academic_id>/user/search_results")
@roles_accepted('editor')
def academic_user_search_results(academic_id, page=1):
    a: Academic = db.get_or_404(Academic, academic_id)

    q = user_search_query({
        'search': get_value_from_all_arguments('search_string') or '',
    })

    q = q.with_only_columns(AcademicUserPicker)

    results = db.paginate(
        select=q,
        page=page,
        per_page=5,
        error_out=False,
    )

    if results.total == 0:
        return render_user_search_add(
            add_url=url_for('ui.academic_user_search_new', academic_id=a.id),
        )

    return render_template(
        "lbrc/search_add_results.html",
        add_title=f"Assign user to '{a.full_name}'",
        add_url=url_for('ui.academic_assign_user', academic_id=a.id),
        results_url='ui.academic_user_search_results',
        results_url_args={'academic_id': a.id},
        results=results,
    )


@blueprint.route("/academic/<int:academic_id>/user/search_new", methods=['GET', 'POST'])
@roles_accepted('editor')
def academic_user_search_new(academic_id):
    a: Academic = db.get_or_404(Academic, academic_id)

    return render_user_search_add(
        add_url=url_for('ui.academic_user_search_new', academic_id=a.id),
        success_callback=partial(academic_user_search_new_success, academic=a)
    )

def academic_user_search_new_success(user: User, academic: Academic):
    academic.user = user
    db.session.add(academic)
    db.session.commit()


@blueprint.route("/academic/<int:academic_id>/assign_user", methods=['POST'])
@roles_accepted('editor')
def academic_assign_user(academic_id):
    a = db.get_or_404(Academic, academic_id)

    id: int = get_value_from_all_arguments('id')
    u = db.get_or_404(User, id)

    a.user_id = u.id

    db.session.add(a)
    db.session.commit()

    return refresh_response()
