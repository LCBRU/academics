from flask import render_template, request
from lbrc_flask.forms import SearchForm
from academics.model import ScopusAuthor, ScopusPublication
from .. import blueprint
from sqlalchemy import or_

@blueprint.route("/author/<int:author_id>/publications/")
def publications(author_id):
    search_form = SearchForm(formdata=request.args)
    
    scopus_author = ScopusAuthor.query.get(author_id)

    q = ScopusPublication.query.filter(ScopusPublication.scopus_authors.any(ScopusAuthor.id == author_id))

    if search_form.search.data:
        q = q.filter(or_(
            ScopusPublication.title.like(f'%{search_form.search.data}%'),
            ScopusPublication.publication.like(f'%{search_form.search.data}%'),
        ))
    q = q.order_by(ScopusPublication.publication_cover_date)

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
