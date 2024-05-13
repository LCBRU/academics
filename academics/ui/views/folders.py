from os import abort
import re
from flask import redirect, render_template, render_template_string, request, url_for
from flask_login import current_user
from lbrc_flask.forms import FlashingForm, SearchForm, ConfirmForm
from sqlalchemy import or_, select
from academics.model.folder import Folder, FolderDoi
from academics.model.security import User
from academics.ui.views.decorators import assert_folder_user
from .. import blueprint
from wtforms import HiddenField, StringField, TextAreaField
from lbrc_flask.database import db
from lbrc_flask.security import current_user_id, system_user_id
from wtforms.validators import Length, DataRequired
from lbrc_flask.response import refresh_response


class FolderEditForm(FlashingForm):
    id = HiddenField('id')
    name = StringField('Name')


class UploadFolderDois(FlashingForm):
    dois = TextAreaField('DOIs', validators=[DataRequired()])


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
        "ui/folder/index.html",
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


@blueprint.route("/folder/<int:id>/remove_shared_user/<int:user_id>", methods=['POST'])
@assert_folder_user()
def folder_remove_shared_user(id, user_id):
    u = db.get_or_404(User, user_id)
    f = db.get_or_404(Folder, id)

    f.shared_users.remove(u)

    db.session.add(f)
    db.session.commit()

    return folder_details(id, 'users')


@blueprint.route("/folder/<int:id>/add_shared_user/<int:user_id>", methods=['POST'])
@assert_folder_user()
def folder_add_shared_user(id, user_id):
    u = db.get_or_404(User, user_id)
    f = db.get_or_404(Folder, id)

    f.shared_users.add(u)

    db.session.add(f)
    db.session.commit()

    return folder_details(id, 'users')


@blueprint.route("/folder/<int:id>/upload_dois", methods=['GET', 'POST'])
@assert_folder_user()
def folder_upload_dois(id):
    form = UploadFolderDois()

    if form.validate_on_submit():
        for doi in filter(None, re.split(',|\s', form.dois.data)):
            doi = doi.strip('.:')
            add_doi_to_folder(id, doi)

        return refresh_response()

    return render_template(
        "form_modal.html",
        title="Upload Folder DOIs",
        form=form,
        url=url_for('ui.folder_upload_dois', id=id),
    )


@blueprint.route("/folder/<int:id>/details/<string:detail_selector>")
def folder_details(id, detail_selector):
    folder = db.get_or_404(Folder, id)

    template = '''
        {% from "ui/folder/_details.html" import render_folder_details with context %}

        {{ render_folder_details(folder, detail_selector, users) }}
    '''

    folder_query = Folder.query

    folder_query = folder_query.filter(or_(
        Folder.owner_id == current_user_id(),
        Folder.shared_users.any(User.id == current_user_id()),
    ))

    return render_template_string(
        template,
        folder=folder,
        detail_selector=detail_selector,
        users=User.query.filter(User.id.notin_([current_user_id(), system_user_id()])).all(),
    )

@blueprint.route("/folder/<int:id>/delete_doi/<string:doi>", methods=['POST'])
def folder_delete_doi(id, doi):
    remove_doi_from_folder(id, doi)

    return folder_details(id, 'dois')


def add_doi_to_folder(folder_id, doi):
    fd = db.session.execute(
        select(FolderDoi)
        .where(FolderDoi.folder_id == folder_id)
        .where(FolderDoi.doi == doi)
    ).scalar_one_or_none()

    if not fd:
        db.session.add(FolderDoi(
            folder_id=folder_id,
            doi=doi,
        ))
        db.session.commit()


def remove_doi_from_folder(folder_id, doi):
    fd = db.session.execute(
        select(FolderDoi)
        .where(FolderDoi.folder_id == folder_id)
        .where(FolderDoi.doi == doi)
    ).scalar_one_or_none()

    if fd:
        db.session.delete(fd)
        db.session.commit()