from os import abort
from flask import redirect, render_template, render_template_string, request
from flask_login import current_user
from lbrc_flask.forms import FlashingForm, SearchForm, ConfirmForm
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload
from academics.model.academic import CatalogPublicationsSources, Source
from academics.model.folder import Folder, FolderDoi
from academics.model.publication import CatalogPublication, Publication
from academics.model.security import User
from academics.ui.views.decorators import assert_folder_user
from .. import blueprint
from wtforms import HiddenField, StringField
from lbrc_flask.database import db
from lbrc_flask.security import current_user_id, system_user_id


class FolderEditForm(FlashingForm):
    id = HiddenField('id')
    name = StringField('Name')


@blueprint.route("/folders/")
def folders():
    search_form = SearchForm(formdata=request.args)
    
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


@blueprint.route("/folder/<int:id>/details/<string:detail_selector>")
@assert_folder_user()
def folder_details(id, detail_selector):
    template = '''
        {% from "ui/folder/_details.html" import render_folder_details with context %}

        {{ render_folder_details(folder, detail_selector, users, folders) }}
    '''

    q = select(Folder).where(
            Folder.id == id
        ).options(
            selectinload(Folder.dois)
            .selectinload(FolderDoi.publication)
            .selectinload(Publication.folder_dois)
            .selectinload(FolderDoi.folder)
        ).options(
            selectinload(Folder.dois)
            .selectinload(FolderDoi.publication)
            .selectinload(Publication.catalog_publications)
            .selectinload(CatalogPublication.catalog_publication_sources)
            .selectinload(CatalogPublicationsSources.source)
            .selectinload(Source.academic)
        )

    folder = db.session.execute(q).scalar_one()

    return render_template_string(
        template,
        folder=folder,
        detail_selector=detail_selector,
        users=User.query.filter(User.id.notin_([current_user_id(), system_user_id()])).all(),
        folders=db.session.execute(select(Folder)).scalars().all(),
    )
