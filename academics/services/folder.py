from lbrc_flask.database import db
from sqlalchemy import or_, select
from academics.model.academic import Academic
from academics.model.folder import Folder, FolderDoi
from academics.model.publication import CatalogPublication, Publication
from academics.model.security import User
from academics.services.publication_searching import catalog_publication_academics
from lbrc_flask.security import current_user_id


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
