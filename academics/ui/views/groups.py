from typing import List
from academics.model.group import Group
from .. import blueprint
from flask import render_template, request, url_for
from flask_login import current_user
from lbrc_flask.forms import FlashingForm, SearchForm, ConfirmForm
from sqlalchemy import or_, select
from academics.model.academic import Academic
from academics.model.security import User
from academics.ui.views.decorators import assert_group_user
from wtforms import HiddenField, StringField
from lbrc_flask.database import db
from lbrc_flask.security import current_user_id, system_user_id
from lbrc_flask.response import refresh_response
from wtforms.validators import Length, DataRequired
from lbrc_flask.requests import get_value_from_all_arguments


class GroupEditForm(FlashingForm):
    id = HiddenField('id')
    name = StringField('Name', validators=[Length(max=1000), DataRequired()])


@blueprint.route("/groups/")
def groups():
    search_form = SearchForm(search_placeholder='Search Group Name', formdata=request.args)
    
    q = select(Group).where(or_(
        Group.owner_id == current_user_id(),
        Group.shared_users.any(User.id == current_user_id()),
    )).order_by(Group.name)

    if search_form.search.data:
        q = q.where(Group.name.like(f'%{search_form.search.data}%'))

    groups = db.paginate(
        select=q,
        page=search_form.page.data,
        per_page=5,
        error_out=False,
    )

    return render_template(
        "ui/group/index.html",
        search_form=search_form,
        groups=groups,
        users=User.query.filter(User.id.notin_([current_user_id(), system_user_id()])).all(),
        edit_folder_form=GroupEditForm(),
        confirm_form=ConfirmForm(),
    )


@blueprint.route("/group/<int:id>/edit", methods=['GET', 'POST'])
@blueprint.route("/group/add", methods=['GET', 'POST'])
@assert_group_user()
def group_edit(id=None):
    if id:
        group = db.get_or_404(Group, id)
        title=f'Edit Group'
    else:
        group = Group()
        group.owner = current_user
        title=f'Add Group'

    form = GroupEditForm(obj=group)

    if form.validate_on_submit():
        group.name = form.name.data

        db.session.add(group)
        db.session.commit()

        return refresh_response()

    return render_template(
        "lbrc/form_modal.html",
        title=title,
        form=form,
        url=url_for('ui.group_edit', id=id),
    )


@blueprint.route("/group/<int:id>/delete", methods=['POST'])
@assert_group_user()
def group_delete(id):
    group = db.get_or_404(Group, id)

    db.session.delete(group)
    db.session.commit()

    return refresh_response()


@blueprint.route("/group/<int:id>/remove_shared_user/<int:user_id>", methods=['POST'])
@assert_group_user()
def group_remove_shared_user(id, user_id):
    u = db.get_or_404(User, user_id)
    g = db.get_or_404(Group, id)

    g.shared_users.remove(u)

    db.session.add(g)
    db.session.commit()

    return refresh_response()


@blueprint.route("/group/<int:id>/add_shared_user/<int:user_id>", methods=['POST'])
@assert_group_user()
def group_add_shared_user(id, user_id):
    u = db.get_or_404(User, user_id)
    g = db.get_or_404(Group, id)

    g.shared_users.add(u)

    db.session.add(g)
    db.session.commit()

    return refresh_response()


@blueprint.route("/group/<int:group_id>/academic/<int:academic_id>/delete", methods=['POST'])
@assert_group_user()
def group_delete_acadmic(group_id, academic_id):
    g: Group = db.get_or_404(Group, group_id)
    a: Academic = db.get_or_404(Academic, academic_id)

    g.academics.remove(a)

    db.session.add(g)
    db.session.commit()

    return refresh_response()


@blueprint.route("/group/<int:group_id>/academic/<int:academic_id>/add", methods=['POST'])
@assert_group_user()
def group_add_acadmic(group_id, academic_id):
    g: Group = db.get_or_404(Group, group_id)
    a: Academic = db.get_or_404(Academic, academic_id)

    g.academics.add(a)

    db.session.add(g)
    db.session.commit()

    return refresh_response()


@blueprint.route("/group/<int:group_id>/academic/search")
@assert_group_user()
def group_acadmic_search(group_id):
    g: Group = db.get_or_404(Group, group_id)

    return render_template(
        "ui/group/academic_search.html",
        group=g,
        search_form=SearchForm(),
    )


@blueprint.route("/group/<int:group_id>/academic/search_results")
@assert_group_user()
def group_acadmic_search_results(group_id, search_string=''):
    g: Group = db.get_or_404(Group, group_id)

    search_string: str = get_value_from_all_arguments('search_string') or ''

    q = (
        select(Academic)
        .where(Academic.id.not_in([a.id for a in g.academics]))
        .where((Academic.first_name + ' ' + Academic.last_name).like(f"%{search_string}%"))
        .where(Academic.initialised == 1)
        .order_by(Academic.last_name, Academic.first_name)
    )

    academics = db.paginate(
        select=q,
        page=1,
        per_page=5,
        error_out=False,
    )

    return render_template(
        "ui/group/academic_search_results.html",
        group=g,
        academics=academics,
    )
