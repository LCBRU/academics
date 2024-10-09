from flask import render_template, render_template_string, request, url_for
from flask_login import current_user
from lbrc_flask.forms import FlashingForm, SearchForm, ConfirmForm
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload
from academics.model.academic import CatalogPublicationsSources, Source
from academics.model.folder import Folder, FolderDoi
from academics.model.publication import CatalogPublication, Publication
from academics.model.security import User
from academics.ui.views.decorators import assert_folder_user
from academics.ui.views.folder_dois import remove_doi_from_folder
from .. import blueprint
from wtforms import HiddenField, StringField
from lbrc_flask.database import db
from lbrc_flask.security import current_user_id, system_user_id
from lbrc_flask.response import refresh_response
from wtforms.validators import Length, DataRequired


class FolderEditForm(FlashingForm):
    id = HiddenField('id')
    name = StringField('Name', validators=[Length(max=1000), DataRequired()])


@blueprint.route("/folders/")
def folders():
    search_form = SearchForm(search_placeholder='Search Name', formdata=request.args)
    
    q = Folder.query

    q = q.filter(or_(
        Folder.owner_id == current_user_id(),
        Folder.shared_users.any(User.id == current_user_id()),
    ))

    if search_form.search.data:
        q = q.filter(Folder.name.like(f'%{search_form.search.data}%'))

    q = q.order_by(Folder.name)

    folders = q.paginate(
        page=search_form.page.data,
        per_page=5,
        error_out=False,
    )

    return render_template(
        "ui/folder/index.html",
        search_form=search_form,
        folders=folders,
        users=User.query.filter(User.id.notin_([current_user_id(), system_user_id()])).all(),
        edit_folder_form=FolderEditForm(),
        confirm_form=ConfirmForm(),
    )


@blueprint.route("/folder/<int:id>/edit", methods=['GET', 'POST'])
@blueprint.route("/folder/add", methods=['GET', 'POST'])
@assert_folder_user()
def folder_edit(id=None):
    if id:
        folder = db.get_or_404(Folder, id)
        title=f'Edit Academic'
    else:
        folder = Folder()
        folder.owner = current_user
        title=f'Add Academic'

    form = FolderEditForm(obj=folder)

    if form.validate_on_submit():
        folder.name = form.name.data

        db.session.add(folder)
        db.session.commit()

        return refresh_response()

    return render_template(
        "lbrc/form_modal.html",
        title=title,
        form=form,
        url=url_for('ui.folder_edit', id=id),
    )


@blueprint.route("/folder/<int:id>/delete", methods=['POST'])
@assert_folder_user()
def folder_delete(id):
    folder = db.get_or_404(Folder, id)

    db.session.delete(folder)
    db.session.commit()

    return refresh_response()


@blueprint.route("/folder/<int:id>/remove_shared_user/<int:user_id>", methods=['POST'])
@assert_folder_user()
def folder_remove_shared_user(id, user_id):
    u = db.get_or_404(User, user_id)
    f = db.get_or_404(Folder, id)

    f.shared_users.remove(u)

    db.session.add(f)
    db.session.commit()

    return refresh_response()


@blueprint.route("/folder/<int:id>/add_shared_user/<int:user_id>", methods=['POST'])
@assert_folder_user()
def folder_add_shared_user(id, user_id):
    u = db.get_or_404(User, user_id)
    f = db.get_or_404(Folder, id)

    f.shared_users.add(u)

    db.session.add(f)
    db.session.commit()

    return refresh_response()


@blueprint.route("/folder/<int:folder_id>/doi/delete_publication/<path:doi>", methods=['POST'])
def folder_delete_publication(folder_id, doi):
    remove_doi_from_folder(folder_id, doi)

    return refresh_response()
