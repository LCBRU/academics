from flask import render_template, request, redirect, url_for
from lbrc_flask.forms import ConfirmForm, FlashingForm, SearchForm
from lbrc_flask.database import db
from wtforms.fields.simple import HiddenField, StringField
from wtforms import SelectField
from academics.scopus.service import add_authors_to_academic, author_search, update_academics, updating
from academics.model import Academic, ScopusAuthor, Theme
from wtforms.validators import Length, DataRequired
from .. import blueprint


def _get_academic_choices():
    academics = Academic.query.all()
    academics = sorted(academics, key=lambda a: ' '.join([a.last_name, a.first_name]))

    return [(0, 'New Academic')] + [(a.id, a.full_name) for a in academics]


class AddAuthorForm(FlashingForm):
    scopus_id = HiddenField()
    academic_id = SelectField('Academic', choices=[], default=0)
    theme_id = SelectField('Theme', coerce=int, validators=[DataRequired()])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.academic_id.choices = _get_academic_choices()
        self.theme_id.choices = [(0, '')] + [(t.id, t.name) for t in Theme.query.all()]


class AcademicEditForm(FlashingForm):
    first_name = StringField("First Name", validators=[Length(max=500)])
    last_name = StringField("Last Name", validators=[Length(max=500)])
    theme_id = SelectField('Theme', coerce=int)

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
        subquery = ScopusAuthor.query.with_entities(ScopusAuthor.academic_id).filter((ScopusAuthor.first_name + ' ' + ScopusAuthor.last_name).like("%{}%".format(search_form.search.data)))
        q = q.filter(Academic.id.in_(subquery))

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
    academic = Academic.query.get_or_404(id)

    form = AcademicEditForm(obj=academic)

    if form.validate_on_submit():
        academic.first_name = form.first_name.data
        academic.last_name = form.last_name.data
        academic.theme_id = form.theme_id.data

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
        authors = author_search(search_form.search.data)

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

    add_authors_to_academic(
        request.form.getlist('scopus_id'),
        form.academic_id.data,
    )

    return redirect(url_for('ui.index'))


@blueprint.route("/delete_academic", methods=['POST'])
def delete_academic():
    form = ConfirmForm()

    if form.validate_on_submit():
        a = Academic.query.get_or_404(form.id.data)
        db.session.delete(a)
        db.session.commit()

    return redirect(url_for('ui.index'))


@blueprint.route("/delete_author", methods=['POST'])
def delete_author():
    form = ConfirmForm()

    if form.validate_on_submit():
        au = ScopusAuthor.query.get_or_404(form.id.data)
        a = au.academic
        db.session.delete(au)
        db.session.flush()

        if not a.scopus_authors:
            db.session.delete(a)

        db.session.commit()

    return redirect(url_for('ui.index'))
