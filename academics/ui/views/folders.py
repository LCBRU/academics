from .. import blueprint
from flask import abort, render_template, request, url_for
from flask_login import current_user
from lbrc_flask.forms import FlashingForm, SearchForm, ConfirmForm
from sqlalchemy import and_, case, distinct, func, literal_column, or_, select
from sqlalchemy.orm import with_expression, Mapped, query_expression, relationship, foreign, joinedload
from academics.model.academic import Academic
from academics.model.folder import Folder, FolderDoi, FolderDoiUserRelevance
from academics.model.publication import CatalogPublication, Publication
from academics.model.security import User
from academics.model.theme import Theme
from academics.services.publication_searching import catalog_publication_academics, catalog_publication_search_query, catalog_publication_themes
from academics.ui.views.decorators import assert_folder_user
from academics.ui.views.folder_dois import remove_doi_from_folder
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
@assert_folder_user()
def folder_delete_publication(folder_id, doi):
    remove_doi_from_folder(folder_id, doi)

    return refresh_response()


class FolderPublicationSearch(SearchForm):
    folder_id = HiddenField()
    academic_id = HiddenField()
    theme_id = HiddenField()
    supress_validation_historic = HiddenField(default=False)


class FolderPublication(Publication):
    folder_doi: Mapped[FolderDoi] = relationship(
        viewonly=True,
        primaryjoin=lambda: FolderPublication.doi == foreign(FolderDoi.doi),
        uselist=False,
    )

    def current_user_relevance(self):
        result = None

        for s in self.folder_doi.user_statuses:
            if s.user_id == current_user_id():
                result = s

        return result


@blueprint.route("/folder/<int:folder_id>/publications")
@blueprint.route("/folder/<int:folder_id>/acadmic/<int:academic_id>/publications")
@blueprint.route("/folder/<int:folder_id>/theme/<int:theme_id>/publications")
@assert_folder_user()
def folder_publications(folder_id, academic_id=None, theme_id=None):
    args = dict(**request.args, folder_id=folder_id, academic_id=academic_id, theme_id=theme_id)
    search_form = FolderPublicationSearch(
        search_placeholder='Search Publications',
        data=args,
    )

    folder = db.get_or_404(Folder, folder_id)
    academic = db.session.execute(select(Academic).where(Academic.id == academic_id)).scalar_one_or_none()
    theme = db.session.execute(select(Theme).where(Theme.id == theme_id)).scalar_one_or_none()

    cat_pubs = catalog_publication_search_query(search_form)

    q = (
        select(FolderPublication)
        .select_from(cat_pubs)
        .join(CatalogPublication, CatalogPublication.id == cat_pubs.c.id)
        .join(CatalogPublication.publication)
        .options(joinedload(FolderPublication.folder_doi.and_(FolderDoi.folder_id == folder.id, FolderDoi.doi == Publication.doi)))
    )

    q = q.order_by(CatalogPublication.publication_cover_date.asc())

    publications = db.paginate(
        select=q,
        page=search_form.page.data,
        per_page=10,
        error_out=False,
    )

    return render_template(
        "ui/folder/publications.html",
        search_form=search_form,
        publications=publications,
        folder=folder,
        academic=academic,
        theme=theme,
    )


class FolderAcademic(Academic):
    folder_publication_count: Mapped[int] = query_expression()
    folder_relevant_count: Mapped[int] = query_expression()
    folder_not_relevant_count: Mapped[int] = query_expression()
    folder_unset_count: Mapped[int] = query_expression()


@blueprint.route("/folder/<int:folder_id>/academics")
@assert_folder_user()
def folder_academics(folder_id):
    args = dict(**request.args, folder_id=folder_id)
    search_form = FolderPublicationSearch(
        search_placeholder='Search Publications',
        data=args,
    )

    folder = db.get_or_404(Folder, folder_id)

    cpa = catalog_publication_academics()

    q = (
        select(FolderAcademic)
        .select_from(cpa)
        .join(CatalogPublication, CatalogPublication.id == cpa.c.catalog_publication_id)
        .join(CatalogPublication.publication)
        .join(Academic, Academic.id == cpa.c.academic_id)
        .join(Publication.folder_dois)
        .join(FolderDoi.folder)
        .join(FolderDoiUserRelevance, and_(
            FolderDoiUserRelevance.folder_doi_id == FolderDoi.id,
            FolderDoiUserRelevance.user_id == Academic.user_id,
        ), isouter=True)
        .where(Folder.id == folder_id)
        .group_by(FolderAcademic.id)
        .order_by(FolderAcademic.last_name, FolderAcademic.first_name)
        .options(with_expression(FolderAcademic.folder_publication_count, func.count(distinct(CatalogPublication.publication_id))))
        .options(with_expression(FolderAcademic.folder_relevant_count, func.sum(case(
            (FolderDoiUserRelevance.relevant, 1),
            else_=0
        ))))
        .options(with_expression(FolderAcademic.folder_not_relevant_count, func.sum(case(
            (FolderDoiUserRelevance.relevant == 0, 1),
            else_=0
        ))))
        .options(with_expression(FolderAcademic.folder_unset_count, func.sum(case(
            (FolderDoiUserRelevance.relevant == None, 1),
            else_=0
        ))))
    )

    academics = db.paginate(
        select=q,
        page=search_form.page.data,
        per_page=20,
        error_out=False,
    )

    return render_template(
        "ui/folder/academics.html",
        search_form=search_form,
        academics=academics,
        folder=folder,
    )


class FolderTheme(Theme):
    folder_publication_count: Mapped[int] = query_expression()


@blueprint.route("/folder/<int:folder_id>/themes")
@assert_folder_user()
def folder_themes(folder_id):
    args = dict(**request.args, folder_id=folder_id)
    search_form = FolderPublicationSearch(
        search_placeholder='Search Publications',
        data=args,
    )

    folder = db.get_or_404(Folder, folder_id)

    cpt = catalog_publication_themes()

    q = (
        select(FolderTheme)
        .select_from(cpt)
        .join(CatalogPublication, CatalogPublication.id == cpt.c.catalog_publication_id)
        .join(CatalogPublication.publication)
        .join(Theme, Theme.id == cpt.c.theme_id)
        .where(Publication.folders.any(Folder.id == folder_id))
        .group_by(FolderTheme.id)
        .order_by(FolderTheme.name)
        .options(with_expression(FolderTheme.folder_publication_count, func.count(distinct(CatalogPublication.publication_id))))
    )

    themes = db.paginate(
        select=q,
        page=search_form.page.data,
        per_page=20,
        error_out=False,
    )

    return render_template(
        "ui/folder/themes.html",
        search_form=search_form,
        themes=themes,
        folder=folder,
    )


@blueprint.route("/folder/<int:folder_id>/relevant/<int:relevant>/doi/<path:doi>", methods=['POST'])
@assert_folder_user()
def folder_doi_set_user_relevance(folder_id, relevant, doi):
    fd = db.session.execute(
        select(FolderDoi)
        .where(FolderDoi.folder_id == folder_id)
        .where(FolderDoi.doi == doi)
        ).scalar_one_or_none()

    if fd is None:
        abort(404)

    fdur = db.session.execute(
        select(FolderDoiUserRelevance)
        .where(FolderDoiUserRelevance.folder_doi_id == fd.id)
        .where(FolderDoiUserRelevance.user_id == current_user_id())
        ).scalar_one_or_none()

    if fdur is None:
        fdur = FolderDoiUserRelevance(
            folder_doi_id=fd.id,
            user_id=current_user_id(),
            relevant=relevant,
        )
    else:
        fdur.relevant = relevant != 0
    
    db.session.add(fdur)
    db.session.commit()

    return refresh_response()
