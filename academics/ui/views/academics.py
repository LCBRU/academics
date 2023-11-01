from flask import abort, jsonify, render_template, request, redirect, url_for
from lbrc_flask.forms import ConfirmForm, FlashingForm, SearchForm
from lbrc_flask.database import db
from wtforms.fields.simple import HiddenField, StringField, BooleanField
from wtforms import SelectField
from academics.catalogs.scopus import scopus_author_search
from academics.catalogs.service import add_sources_to_academic, delete_orphan_publications, update_academics, update_single_academic, updating
from academics.model import Academic, AcademicPotentialSource, Source, Theme
from wtforms.validators import Length
from .. import blueprint
from lbrc_flask.json import validate_json


def _get_academic_choices():
    academics = Academic.query.all()
    academics = sorted(academics, key=lambda a: ' '.join([a.last_name, a.first_name]))

    return [(0, 'New Academic')] + [(a.id, a.full_name) for a in academics]


class AddAuthorForm(FlashingForm):
    catalog_identifier = HiddenField()
    academic_id = SelectField('Academic', choices=[], default=0)
    theme_id = SelectField('Theme', coerce=int)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.academic_id.choices = _get_academic_choices()
        self.theme_id.choices = [(0, '')] + [(t.id, t.name) for t in Theme.query.all()]


class AcademicEditForm(FlashingForm):
    first_name = StringField("First Name", validators=[Length(max=500)])
    last_name = StringField("Last Name", validators=[Length(max=500)])
    orcid = StringField("ORCID", validators=[Length(max=255)])
    theme_id = SelectField('Theme', coerce=int)
    has_left_brc = BooleanField('Has Left BRC', default=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.theme_id.choices = [(0, '')] + [(t.id, t.name) for t in Theme.query.all()]


class AcademicSearchForm(SearchForm):
    theme_id = SelectField('Theme', coerce=int)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.theme_id.choices = [(0, ''), (-1, '[Unset]')] + [(t.id, t.name) for t in Theme.query.all()]


@blueprint.route("/")
def index():
    search_form = AcademicSearchForm(formdata=request.args)

    q = Academic.query
    q = q.filter(Academic.initialised == True)

    if search_form.search.data:
        q = q.filter((Academic.first_name + ' ' + Academic.last_name).like("%{}%".format(search_form.search.data)))

    if search_form.theme_id.data:
        if search_form.theme_id.data == -1:
            q = q.filter(Academic.theme_id == None)
        else:
            q = q.filter(Academic.theme_id == search_form.theme_id.data)

    academics = q.paginate(
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

    form = AcademicEditForm(obj=academic)

    if form.validate_on_submit():
        academic.first_name = form.first_name.data
        academic.last_name = form.last_name.data
        academic.orcid = form.orcid.data
        academic.theme_id = form.theme_id.data
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
        request.form.getlist('catalog_identifier'),
        form.academic_id.data,
        form.theme_id.data,
    )

    return redirect(url_for('ui.index'))


@blueprint.route("/delete_academic", methods=['POST'])
def delete_academic():
    form = ConfirmForm()

    if form.validate_on_submit():
        a = db.get_or_404(Academic, form.id.data)
        db.session.delete(a)
        db.session.commit()

        delete_orphan_publications()

    return redirect(url_for('ui.index'))


@blueprint.route("/delete_author", methods=['POST'])
def delete_author():
    form = ConfirmForm()

    if form.validate_on_submit():
        s = db.get_or_404(Source, form.id.data)
        db.session.delete(s)
        db.session.commit()

        delete_orphan_publications()

    return redirect(url_for('ui.index'))


@blueprint.route("/update_academic", methods=['POST'])
def update_academic():
    form = ConfirmForm()

    if form.validate_on_submit():
        academic = db.get_or_404(Academic, form.id.data)

    update_single_academic(academic)

    return redirect(url_for('ui.index'))


@blueprint.route("/academics/<int:id>/potential_sources")
def academics_potential_sources(id):
    a = db.session.get(Academic, id)

    print(a)

    if not a:
        abort(404)

    return render_template(
        "ui/potential_sources.html",
        academic=a,
    )


@blueprint.route("/academics/amend_potential_sources", methods=['POST'])
@validate_json({
    'type': 'object',
    'properties': {
        'id': {'type': 'integer'},
        'academic_id': {'type': 'integer'},
        'status': {'type': 'string'},
    },
    "required": ["id", "academic_id", "status"]
})
def academics_amend_potential_sources():
    ps : AcademicPotentialSource = db.get_or_404(AcademicPotentialSource, request.json.get('id'))
    a : Academic = db.get_or_404(Academic, request.json.get('academic_id'))
    status = request.json.get('status').lower()

    UNASSIGNED = 'unassigned'
    NO_MATCH = 'no match'
    MATCH = 'match'

    ALL_STATUSES = {UNASSIGNED, NO_MATCH, MATCH}

    if status not in ALL_STATUSES:
        abort(406, f"Status not recognised should be {ALL_STATUSES}, but is {status}")

    if ps.source.academic and ps.source.academic != a:
        abort(406, f"Academic does not match source academic of {ps.source.academic.full_name}, but is {a.full_name}")

    match request.json.get('status').lower():
        case 'unassigned':
            ps.source.academic = None
            ps.not_match = False
        case 'no match':
            ps.source.academic = None
            ps.not_match = True
        case 'match':
            ps.source.academic = a
            ps.not_match = False
    
    db.session.add(ps)
    db.session.commit()

    return jsonify({'status': request.json.get('status')}), 200


