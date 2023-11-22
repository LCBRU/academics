from os import abort
from flask import jsonify, redirect, render_template, request
from flask_login import current_user
from lbrc_flask.forms import FlashingForm, SearchForm, ConfirmForm
from sqlalchemy import or_
from academics.model import Folder, Publication, User
from academics.ui.views.decorators import assert_folder_user
from .. import blueprint
from wtforms import HiddenField, StringField
from lbrc_flask.database import db
from lbrc_flask.json import validate_json
from lbrc_flask.security import current_user_id, system_user_id


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
        users=User.query.filter(User.id.notin_([current_user_id(), system_user_id()])).all(),
        edit_folder_form=FolderEditForm(),
        confirm_form=ConfirmForm(),
    )


def _get_folder_query(search_form):
    q = Folder.query

    q = q.filter(or_(
        Folder.owner_id == current_user_id(),
        Folder.shared_users.any(User.id == current_user_id()),
    ))

    if search_form.search.data:
        q = q.filter(Folder.name.like(f'%{search_form.search.data}%'))

    return q


@blueprint.route("/folders/save", methods=['POST'])
def folder_save():
    form = FolderEditForm()

    if form.validate_on_submit():
        id = form.id.data

        if id:
            folder = db.get_or_404(Folder, id)
        else:
            folder = Folder()
            folder.owner = current_user

        if folder.owner != current_user:
            abort(403)

        folder.name = form.name.data

        db.session.add(folder)
        db.session.commit()

    return redirect(request.referrer)


@blueprint.route("/folders/delete", methods=['POST'])
@assert_folder_user()
def folder_delete():
    form = ConfirmForm()

    if form.validate_on_submit():
        folder = db.get_or_404(Folder, form.id.data)

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
@assert_folder_user()
def folder_remove_publication():
    p = db.get_or_404(Publication, request.json.get('publication_id'))
    f = db.get_or_404(Folder, request.json.get('folder_id'))

    f.publications.remove(p)

    db.session.add(f)
    db.session.commit()

    return jsonify({}), 200


@blueprint.route("/folder/add_publication", methods=['POST'])
@validate_json({
    'type': 'object',
    'properties': {
        'folder_id': {'type': 'integer'},
        'scopus_publication_id': {'type': 'integer'},
    },
    "required": ["folder_id", "scopus_publication_id"]
})
@assert_folder_user()
def folder_add_publication():
    p = db.get_or_404(Publication, request.json.get('publication_id'))
    f = db.get_or_404(Folder, request.json.get('folder_id'))

    f.publications.add(p)

    db.session.add(f)
    db.session.commit()

    return jsonify({}), 200


@blueprint.route("/folder/users", methods=['POST'])
@validate_json({
    'type': 'object',
    'properties': {
        'id': {'type': 'integer'},
    },
    "required": ["id"]
})
def folder_users():
    folder = db.get_or_404(Folder, request.json.get('id'))

    resp = render_template(
        "ui/folder_users.html",
        folder=folder,
        users=User.query.filter(User.id.notin_([current_user_id(), system_user_id()])).all(),
    )

    return resp


@blueprint.route("/folder/remove_shared_user", methods=['POST'])
@validate_json({
    'type': 'object',
    'properties': {
        'folder_id': {'type': 'integer'},
        'user_id': {'type': 'integer'},
    },
    "required": ["folder_id", "user_id"]
})
@assert_folder_user()
def folder_remove_shared_user():
    u = db.get_or_404(User, request.json.get('user_id'))
    f = db.get_or_404(Folder, request.json.get('folder_id'))

    f.shared_users.remove(u)

    db.session.add(f)
    db.session.commit()

    return jsonify({}), 205


@blueprint.route("/folder/add_shared_user", methods=['POST'])
@validate_json({
    'type': 'object',
    'properties': {
        'folder_id': {'type': 'integer'},
        'user_id': {'type': 'integer'},
    },
    "required": ["folder_id", "user_id"]
})
@assert_folder_user()
def folder_add_shared_user():
    u = db.get_or_404(User, request.json.get('user_id'))
    f = db.get_or_404(Folder, request.json.get('folder_id'))

    f.shared_users.add(u)

    db.session.add(f)
    db.session.commit()

    return jsonify({}), 205
