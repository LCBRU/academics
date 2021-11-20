from flask import render_template, request, redirect, url_for
from lbrc_flask.forms import ConfirmForm, FlashingForm, SearchForm
from lbrc_flask.database import db
from wtforms.fields.simple import HiddenField
from wtforms import SelectField
from academics.scopus.service import author_search, get_author, invoke_update_all_academics
from academics.model import Academic, ScopusAuthor
from .. import blueprint


def _get_academic_choices():
    academics = Academic.query.all()
    academics = sorted(academics, key=lambda a: ' '.join([a.last_name, a.first_name]))

    return [(0, 'New Academic')] + [(a.id, a.full_name) for a in academics]


class AddAuthorForm(FlashingForm):
    scopus_id = HiddenField()
    academic_id = SelectField('Academic', coerce=int, choices=[], default=0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.academic_id.choices = _get_academic_choices()


@blueprint.route("/")
def index():
    search_form = SearchForm(formdata=request.args)

    q = Academic.query.distinct().join(Academic.scopus_authors)

    if search_form.search.data:
        q = q.filter((ScopusAuthor.first_name + ' ' + ScopusAuthor.last_name).like("%{}%".format(search_form.search.data)))

    q = q.order_by(ScopusAuthor.first_name + ' ' + ScopusAuthor.last_name)

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
    )


@blueprint.route("/update_all_academics")
def update_all_academics():
    invoke_update_all_academics()
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

    if form.academic_id.data:
        academic = Academic.query.get_or_404(form.academic_id.data)
    else:
        academic = Academic()

    for id in request.form.getlist('scopus_id'):
        author = get_author(id).get_scopus_author()
        author.academic = academic

        db.session.add(author)
        db.session.commit()

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
        a = ScopusAuthor.query.get_or_404(form.id.data)
        db.session.delete(a)
        db.session.commit()

    return redirect(url_for('ui.index'))
