from flask import render_template, request, redirect, url_for
from sqlalchemy import func
from lbrc_flask.forms import SearchForm
from lbrc_flask.database import db
from academics.scopus.service import author_search, get_author
from academics.model import Academic
from .. import blueprint


@blueprint.route("/")
def index():
    search_form = SearchForm(formdata=request.args)

    q = Academic.query

    if search_form.search.data:
        q = q.filter(Academic.first_name + ' ' + Academic.last_name).like("%{}%".format(search_form.search.data))

    q = q.order_by(Academic.first_name + ' ' + Academic.last_name)

    academics = q.paginate(
            page=search_form.page.data,
            per_page=5,
            error_out=False,
        )

    return render_template("ui/index.html", academics=academics, search_form=search_form)


@blueprint.route("/add_author_search")
def add_author_search():
    search_form = SearchForm(formdata=request.args)

    authors = []

    if search_form.search.data:
        authors = author_search(search_form.search.data)

    return render_template("ui/add_author_search.html", authors=authors, search_form=search_form)


@blueprint.route("/add_author/<string:scopus_id>", methods=['POST'])
def add_author(scopus_id):

    author = get_author(scopus_id)

    academic = author.get_academic()

    db.session.add(academic)
    db.session.commit()

    return redirect(url_for('ui.index'))
