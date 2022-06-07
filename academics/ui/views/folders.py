from flask import jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from lbrc_flask.forms import FlashingForm, SearchForm, ConfirmForm
from academics.model import Folder, ScopusPublication
from .. import blueprint
from wtforms import HiddenField, StringField
from lbrc_flask.database import db
from lbrc_flask.json import validate_json


class FolderEditForm(FlashingForm):
    id = HiddenField('id')
    name = StringField('Name')


@blueprint.route("/folders/")
def folders():
    search_form = SearchForm(formdata=request.args)
    
    q = _get_folder_query(search_form)

    q = q.order_by(Folder.name)

    folders = q.paginate(
        page=search_form.page.data,
        per_page=5,
        error_out=False,
    )

    return render_template(
        "ui/folders.html",
        search_form=search_form,
        folders=folders,
        edit_folder_form=FolderEditForm(),
        confirm_form=ConfirmForm(),
    )


def _get_folder_query(search_form):
    q = Folder.query.filter(Folder.owner == current_user)

    if search_form.search.data:
        q = q.filter(Folder.name.like(f'%{search_form.search.data}%'))

    return q


@blueprint.route("/folders/save", methods=['POST'])
def folder_save():
    form = FolderEditForm()

    if form.validate_on_submit():
        id = form.id.data

        if id:
            folder = Folder.query.get_or_404(id)
        else:
            folder = Folder()
            folder.owner = current_user

        folder.name = form.name.data

        db.session.add(folder)
        db.session.commit()

    return redirect(request.referrer)


@blueprint.route("/folders/delete", methods=['POST'])
def folder_delete():
    form = ConfirmForm()

    if form.validate_on_submit():
        folder = Folder.query.get_or_404(form.id.data)

        db.session.delete(folder)
        db.session.commit()

    return redirect(request.referrer)


@blueprint.route("/folder/remove_publication", methods=['POST'])
@validate_json({
    'type': 'object',
    'properties': {
        'folder_id': {'type': 'integer'},
        'scopus_publication_id': {'type': 'integer'},
    },
    "required": ["folder_id", "scopus_publication_id"]
})
def folder_remove_publication():
    p = ScopusPublication.query.get_or_404(request.json.get('scopus_publication_id'))
    f = Folder.query.get_or_404(request.json.get('folder_id'))

    f.publications.remove(p)

    db.session.add(f)
    db.session.commit()

    return jsonify({}), 205


@blueprint.route("/folder/add_publication", methods=['POST'])
@validate_json({
    'type': 'object',
    'properties': {
        'folder_id': {'type': 'integer'},
        'scopus_publication_id': {'type': 'integer'},
    },
    "required": ["folder_id", "scopus_publication_id"]
})
def folder_add_publication():
    p = ScopusPublication.query.get_or_404(request.json.get('scopus_publication_id'))
    f = Folder.query.get_or_404(request.json.get('folder_id'))

    f.publications.add(p)

    db.session.add(f)
    db.session.commit()

    return jsonify({}), 205