from flask import render_template, request, redirect, url_for
from lbrc_flask.forms import FlashingForm, SearchForm
from lbrc_flask.database import db
from wtforms.fields.simple import HiddenField
from academics.scopus.service import author_search, get_author, invoke_update_all_academics
from academics.model import Academic, ScopusAuthor
from .. import blueprint


class AddAuthorToNewAcademicForm(FlashingForm):
    scopus_id = HiddenField()


class AddAuthorToAcademicForm(FlashingForm):
    scopus_id = HiddenField()
    academic_id = HiddenField()


@blueprint.route("/")
def index():
    search_form = SearchForm(formdata=request.args)

    q = Academic.query.distinct().join(Academic.scopus_authors)

    if search_form.search.data:
        q = q.filter(ScopusAuthor.first_name + ' ' + ScopusAuthor.last_name).like("%{}%".format(search_form.search.data))

    q = q.order_by(ScopusAuthor.first_name + ' ' + ScopusAuthor.last_name)

    academics = q.paginate(
            page=search_form.page.data,
            per_page=5,
            error_out=False,
        )

    return render_template("ui/index.html", academics=academics, search_form=search_form)


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
        add_author_to_new_academic_form=AddAuthorToNewAcademicForm(),
        add_author_to_academic_form=AddAuthorToAcademicForm()
    )


@blueprint.route("/add_author_to_new_academic", methods=['POST'])
def add_author_to_new_academic():
    form = AddAuthorToNewAcademicForm()

    return _add_author_to_academic(form.scopus_id.data, Academic())


@blueprint.route("/add_author_to_academic", methods=['POST'])
def add_author_to_academic():
    form = AddAuthorToAcademicForm()

    academic = Academic.query.get_or_404(form.academic_id.data)

    return _add_author_to_academic(form.scopus_id.data, academic)


def _add_author_to_academic(scopus_id, academic):

    author = get_author(scopus_id).get_scopus_author()
    author.academic = academic

    db.session.add(author)
    db.session.commit()

    return redirect(url_for('ui.index'))
