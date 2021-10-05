from flask import render_template, request, redirect, url_for
from lbrc_flask.forms import SearchForm
from academics.service import author_search
from .. import blueprint


@blueprint.route("/")
def index():
    search_form = SearchForm(formdata=request.args)

    return render_template("ui/index.html", search_form=search_form)


@blueprint.route("/add_author_search")
def add_author_search():
    search_form = SearchForm(formdata=request.args)

    authors = []

    if search_form.search.data:
        authors = author_search(search_form.search.data)

    print(authors)

    return render_template("ui/add_author_search.html", authors=authors, search_form=search_form)


@blueprint.route("/add_author")
def add_author(id):

    return redirect(url_for('ui.index'))
