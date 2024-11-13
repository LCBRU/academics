from lbrc_flask.database import db
from sqlalchemy import select
from academics.model.academic import Academic
from academics.model.folder import FolderDoi
from academics.model.publication import CatalogPublication, Publication
from academics.model.security import User
from academics.services.publication_searching import catalog_publication_academics


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
