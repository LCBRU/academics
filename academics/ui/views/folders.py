from academics.ui.views.users import render_user_search_results, user_search_query
from .. import blueprint
from flask import abort, render_template, request, url_for
from flask_login import current_user
from lbrc_flask.forms import FlashingForm, SearchForm
from sqlalchemy import and_, case, distinct, func, or_, select
from sqlalchemy.orm import with_expression, Mapped, query_expression, relationship, foreign, joinedload, selectinload
from academics.model.academic import Academic, CatalogPublicationsSources, Source
from academics.model.folder import Folder, FolderDoi, FolderDoiUserRelevance
from academics.model.publication import CatalogPublication, Publication
from academics.model.security import User
from academics.model.theme import Theme
from academics.services.publication_searching import catalog_publication_academics, catalog_publication_search_query, catalog_publication_themes
from academics.ui.views.decorators import assert_folder_user
from academics.ui.views.folder_dois import add_doi_to_folder, remove_doi_from_folder
from wtforms import DateField, HiddenField, SelectField, StringField, TextAreaField
from lbrc_flask.database import db
from lbrc_flask.security import current_user_id, system_user_id
from lbrc_flask.response import refresh_response
from lbrc_flask.validators import is_invalid_doi
from wtforms.validators import Length, DataRequired, Optional
from lbrc_flask.requests import get_value_from_all_arguments
from datetime import date


class FolderEditForm(FlashingForm):
    id = HiddenField('id')
    name = StringField('Name', validators=[Length(max=1000), DataRequired()])
    description = TextAreaField('Description', validators=[Length(max=1000)])
    autofill_year = SelectField('Autofill Year', coerce=int, default=None, validators=[Optional()])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.autofill_year.choices = [(0, '')] + [(y, f'April {y} to March {y+1}') for y in range(2024, date.today().year + 2)]


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
    )


@blueprint.route("/folder/<int:id>/edit", methods=['GET', 'POST'])
@blueprint.route("/folder/add", methods=['GET', 'POST'])
@assert_folder_user()
def folder_edit(id=None):
    if id:
        folder = db.get_or_404(Folder, id)
        title=f'Edit Folder'
    else:
        folder = Folder()
        folder.owner = current_user
        title=f'Add Folder'

    form = FolderEditForm(obj=folder)

    if form.validate_on_submit():
        folder.name = form.name.data
        folder.description = form.description.data

        if form.autofill_year.data:
            folder.autofill_year = form.autofill_year.data
        else:
            folder.autofill_year = None

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


@blueprint.route("/folder/<int:folder_id>/shared_user/search")
@assert_folder_user()
def folder_shared_user_search(folder_id):
    f: Folder = db.get_or_404(Folder, folder_id)

    return render_template(
        "lbrc/search.html",
        title=f"Add Shared User to Folder '{f.name}'",
        results_url=url_for('ui.folder_shared_user_search_results', folder_id=f.id),
    )


@blueprint.route("/folder/<int:folder_id>/shared_user/search_results/<int:page>")
@blueprint.route("/folder/<int:folder_id>/shared_user/search_results")
@assert_folder_user()
def folder_shared_user_search_results(folder_id, page=1):
    f: Folder = db.get_or_404(Folder, folder_id)

    q = user_search_query(get_value_from_all_arguments('search_string') or '',)
    q = q.where(User.id.not_in([u.id for u in f.shared_users]))

    results = db.paginate(
        select=q,
        page=page,
        per_page=5,
        error_out=False,
    )

    return render_user_search_results(
        results=results,
        title="Add shared user to folder '{f.name}'",
        add_url=url_for('ui.folder_add_shared_user', folder_id=f.id),
        results_url='ui.folder_shared_user_search_results',
        results_url_args={'folder_id': f.id},
    )


@blueprint.route("/folder/<int:id>/remove_shared_user/<int:user_id>", methods=['POST'])
@assert_folder_user()
def folder_remove_shared_user(id, user_id):
    u = db.get_or_404(User, user_id)
    f = db.get_or_404(Folder, id)

    f.shared_users.remove(u)

    db.session.add(f)
    db.session.commit()

    return refresh_response()


@blueprint.route("/folder/<int:folder_id>/add_shared_user", methods=['POST'])
@assert_folder_user()
def folder_add_shared_user(folder_id):
    f = db.get_or_404(Folder, folder_id)

    id: int = get_value_from_all_arguments('id')
    u = db.get_or_404(User, id)

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

    q = q.options(
        selectinload(Publication.catalog_publications)
        .selectinload(CatalogPublication.catalog_publication_sources)
        .selectinload(CatalogPublicationsSources.source)
        .selectinload(Source.academic)
    )

    q = q.order_by(CatalogPublication.publication_cover_date.asc(), CatalogPublication.id)

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
        .options(with_expression(FolderAcademic.folder_relevant_count, func.count(distinct(case(
            (FolderDoiUserRelevance.relevant, CatalogPublication.publication_id),
            else_=None
        )))))
        .options(with_expression(FolderAcademic.folder_not_relevant_count, func.count(distinct(case(
            (FolderDoiUserRelevance.relevant == 0, CatalogPublication.publication_id),
            else_=None
        )))))
        .options(with_expression(FolderAcademic.folder_unset_count, func.count(distinct(case(
            (FolderDoiUserRelevance.relevant == None, CatalogPublication.publication_id),
            else_=None
        )))))
        .options(selectinload(Academic.user))
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


@blueprint.route("/folder/<int:folder_id>/publication/add_search")
@assert_folder_user()
def folder_add_publication_add_search(folder_id):
    f: Folder = db.get_or_404(Folder, folder_id)

    return render_template(
        "lbrc/search.html",
        title=f"Add Publication to Folder '{f.name}'",
        search_placeholder='Search Publication DOI ...',
        results_url=url_for('ui.folder_add_publication_add_search_results', folder_id=f.id),
    )


class FolderNewPublicationForm(FlashingForm):
    folder_id = HiddenField('folder_id')
    doi = HiddenField('doi')
    title = TextAreaField('Title', validators=[Length(max=1000)])
    publication_cover_date = DateField('Publication Cover Date', validators=[Optional()])


class PublicationPicker(Publication):
    @property
    def name(self):
        return self.doi


@blueprint.route("/folder/<int:folder_id>/publication/add_search_results/<int:page>")
@blueprint.route("/folder/<int:folder_id>/publication/add_search_results")
@assert_folder_user()
def folder_add_publication_add_search_results(folder_id, page=1):
    f: Folder = db.get_or_404(Folder, folder_id)

    search_string: str = get_value_from_all_arguments('search_string') or ''

    q = (
        select(PublicationPicker)
        .where(Publication.doi.not_in([fd.doi for fd in f.dois]))
        .where(Publication.doi.like(f"%{search_string}%"))
        .order_by(Publication.doi)
    )

    results = db.paginate(
        select=q,
        page=page,
        per_page=5,
        error_out=False,
    )

    if results.total == 0:
        if is_invalid_doi(search_string):
            return "<h6>Invalid DOI</h6>"
        else:
            return render_template(
                "lbrc/search_form_result.html",
                url=url_for('ui.catalog_publication_edit'),
                form=FolderNewPublicationForm(data={
                    'folder_id': folder_id,
                    'doi': search_string,
                }),
            )

    return render_template(
        "lbrc/search_add_results.html",
        add_title="Add publication to folder '{f.name}'",
        add_url=url_for('ui.folder_add_publication', folder_id=f.id),
        results_url='ui.folder_add_publication_add_search_results',
        results_url_args={'folder_id': f.id},
        results=results,
    )


@blueprint.route("/folder/<int:folder_id>/publication/add", methods=['POST'])
def folder_add_publication(folder_id):
    f: Folder = db.get_or_404(Folder, folder_id)

    id: int = get_value_from_all_arguments('id')
    p: Publication = db.get_or_404(Publication, id)

    add_doi_to_folder(f.id, p.doi)

    return refresh_response()
