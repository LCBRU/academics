from datetime import datetime, timezone
from typing import Optional
from lbrc_flask.database import db
from sqlalchemy import distinct, func, or_, select
from wtforms import HiddenField
from academics.jobs.catalogs import CatalogPublicationRefresh
from academics.model.academic import Academic, CatalogPublicationsSources, Source
from academics.model.folder import Folder, FolderDoi, FolderExcludedDoi
from academics.model.publication import CatalogPublication, Publication
from academics.model.security import User
from academics.model.theme import Theme
from academics.services.publication_searching import catalog_publication_academics, catalog_publication_search_query, catalog_publication_themes, publication_folder_query
from lbrc_flask.security import current_user_id
from sqlalchemy.orm import with_expression, Mapped, query_expression, relationship, foreign, joinedload
from lbrc_flask.forms import SearchForm
from lbrc_flask.requests import all_args
from lbrc_flask.async_jobs import AsyncJobs, run_jobs_asynch


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
    cat_pubs = catalog_publication_search_query(search_form).subquery()

    q = (
        select(FolderPublication)
        .select_from(cat_pubs)
        .join(CatalogPublication, CatalogPublication.id == cat_pubs.c.id)
        .join(CatalogPublication.publication)
        .options(joinedload(FolderPublication.folder_doi.and_(
            FolderDoi.folder_id == folder.id,
            FolderDoi.doi == Publication.doi,
        )))
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


def folder_theme_search_query(folder: Folder, search_form: FolderThemeSearchForm):
    cpt = catalog_publication_themes()

    q = (
        select(FolderTheme)
        .select_from(cpt)
        .join(CatalogPublication, CatalogPublication.id == cpt.c.catalog_publication_id)
        .join(CatalogPublication.publication)
        .join(Theme, Theme.id == cpt.c.theme_id)
        .where(Publication.folders.any(Folder.id == folder.id))
        .group_by(FolderTheme.id)
        .order_by(FolderTheme.name)
        .options(with_expression(FolderTheme.folder_publication_count, func.count(distinct(CatalogPublication.publication_id))))
    )

    for w in search_form.search_words:
        q = q.where(Theme.name.like(f"%{w}%"))

    return q


def add_dois_to_folder(folder_id, dois):
    for doi in dois:
        add_doi_to_folder(folder_id, doi)


def add_doi_to_folder(folder_id, doi):
    fd = get_folder_doi(folder_id, doi)

    if not fd:
        db.session.add(FolderDoi(
            folder_id=folder_id,
            doi=doi,
        ))


def remove_doi_from_folder(folder_id, doi):
    fd = get_folder_doi(folder_id, doi)

    if fd:
        db.session.delete(fd)
        exclude_doi_from_folder(folder_id, doi)


def exclude_doi_from_folder(folder_id, doi):
    edf = get_folder_excluded_doi(folder_id, doi)

    if not edf:
        db.session.add(FolderExcludedDoi(
            folder_id=folder_id,
            doi=doi,
        ))


def get_folder_excluded_doi(folder_id, doi) -> FolderExcludedDoi:
    return db.session.execute(
        select(FolderExcludedDoi)
        .where(FolderExcludedDoi.folder_id == folder_id)
        .where(FolderExcludedDoi.doi == doi)
    ).scalar_one_or_none()


def get_folder_doi(folder_id, doi) -> FolderDoi:
    return db.session.execute(
        select(FolderDoi)
        .where(FolderDoi.folder_id == folder_id)
        .where(FolderDoi.doi == doi)
    ).scalar_one_or_none()


def create_publication_folder(publications):
    folder = Folder(
        name=f'Publication Search {datetime.now(timezone.utc):%Y%m%d_%H%M%S}',
        owner_id=current_user_id(),
    )
    db.session.add(folder)
    db.session.flush()

    db.session.add_all([
        FolderDoi(folder_id=folder.id, doi=p.doi) for p in publications
    ])

    return folder


def is_folder_name_duplicate(name: str, folder_id: Optional[int]):
    q = (
        select(func.count(Folder.id))
        .where(Folder.name == name)
        .where(Folder.owner_id == current_user_id())
    )

    if folder_id is not None:
        q = q.where(Folder.id != folder_id)

    return db.session.execute(q).scalar() > 0


def folder_academic_query():
    pfq = publication_folder_query()

    q = (
        select(
            pfq.c.folder_id,
            Academic.id.label('academic_id'),
        ).select_from(pfq)
        .join(CatalogPublication, CatalogPublication.publication_id == pfq.c.publication_id)
        .join(CatalogPublication.catalog_publication_sources)
        .join(CatalogPublicationsSources.source)
        .join(Source.academic)
    )

    return q


def folder_scheule_update_publications(folder):
    q = (
        select(CatalogPublication)
        .where(CatalogPublication.doi.in_(
            select(FolderDoi.doi)
            .where(FolderDoi.folder_id == folder.id)
        ))
    )

    for cp in db.session.execute(q).scalars():
        AsyncJobs.schedule(CatalogPublicationRefresh(cp))
    
    db.session.commit()

    run_jobs_asynch()
