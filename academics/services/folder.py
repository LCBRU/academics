from lbrc_flask.database import db
from sqlalchemy import and_, case, distinct, func, or_, select
from wtforms import HiddenField
from academics.model.academic import Academic
from academics.model.folder import Folder, FolderDoi, FolderDoiUserRelevance
from academics.model.publication import CatalogPublication, Publication
from academics.model.security import User
from academics.model.theme import Theme
from academics.services.publication_searching import catalog_publication_academics, catalog_publication_search_query, catalog_publication_themes
from lbrc_flask.security import current_user_id
from sqlalchemy.orm import with_expression, Mapped, query_expression, relationship, foreign, joinedload
from lbrc_flask.forms import SearchForm
from lbrc_flask.requests import all_args


def folder_author_users(folder):
    cpa = catalog_publication_academics()

    return db.session.execute(
        select(User)
        .select_from(cpa)
        .join(CatalogPublication, CatalogPublication.id == cpa.c.catalog_publication_id)
        .join(CatalogPublication.publication)
        .join(Academic, Academic.id == cpa.c.academic_id)
        .join(Academic.user)
        .join(Publication.folder_dois)
        .where(FolderDoi.folder_id == folder.id)
        ).unique().scalars()


def current_user_folders_search_query(search_form):
    q = (
        select(Folder)
        .where(or_(
            Folder.owner_id == current_user_id(),
            Folder.shared_users.any(User.id == current_user_id()),
        ))
        .order_by(Folder.name)
    )

    if search_form.search.data:
        q = q.where(Folder.name.like(f'%{search_form.search.data}%'))

    return q


class FolderAcademic(Academic):
    folder_publication_count: Mapped[int] = query_expression()
    folder_relevant_count: Mapped[int] = query_expression()
    folder_not_relevant_count: Mapped[int] = query_expression()
    folder_unset_count: Mapped[int] = query_expression()


class FolderAcademicSearchForm(SearchForm):
    def __init__(self, **kwargs):
        super().__init__(
            search_placeholder="Search Folder Academics",
            data=all_args(),
        )


def folder_academics_search_query(folder_id: int, search_form: FolderAcademicSearchForm):
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
        .group_by(Academic.id)
        .order_by(Academic.last_name, Academic.first_name)
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
    )

    for w in search_form.search_words:
        q = q.where(or_(
            Academic.first_name.like(f"%{w}%"),
            Academic.last_name.like(f"%{w}%"),
        ))

    return q


class FolderPublicationSearchForm(SearchForm):
    def __init__(self, **kwargs):
        super().__init__(
            search_placeholder="Search Publications",
            data=all_args(),
            )

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


def folder_publication_search_query(folder: Folder, search_form: FolderPublicationSearchForm):
    cat_pubs = catalog_publication_search_query(search_form)

    q = (
        select(FolderPublication)
        .select_from(cat_pubs)
        .join(CatalogPublication, CatalogPublication.id == cat_pubs.c.id)
        .join(CatalogPublication.publication)
        .options(joinedload(FolderPublication.folder_doi.and_(FolderDoi.folder_id == folder.id, FolderDoi.doi == Publication.doi)))
        .order_by(CatalogPublication.publication_cover_date.asc(), CatalogPublication.id)
    )

    return q


class FolderTheme(Theme):
    folder_publication_count: Mapped[int] = query_expression()


class FolderThemeSearchForm(SearchForm):
    def __init__(self, **kwargs):
        super().__init__(
            search_placeholder="Search Themes",
            data=all_args(),
            )


def folder_publication_search_query(folder_id: int, search_form: FolderThemeSearchForm):
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

    for w in search_form.search_words:
        q = q.where(Theme.name.like(f"%{w}%"))

    return q
