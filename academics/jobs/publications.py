from datetime import date, datetime, timezone
from lbrc_flask.async_jobs import AsyncJob
from lbrc_flask.database import db
from sqlalchemy import delete, select
from academics.services.publication_searching import best_catalog_publications
from academics.model.folder import Folder, FolderDoi, FolderExcludedDoi
from academics.model.publication import CatalogPublication, Publication


class PublicationRemoveUnused(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "PublicationRemoveUnused",
    }

    def __init__(self):
        super().__init__(
            scheduled=datetime.now(timezone.utc),
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='1',
        )

    def _run_actual(self):
        pubs_without_catalog = db.session.execute(
            select(Publication.id)
            .where(Publication.id.not_in(select(CatalogPublication.publication_id)))
        ).scalars().all()

        db.session.execute(
            delete(FolderDoi)
            .where(FolderDoi.publication.has(Publication.id.in_(pubs_without_catalog)))
        )

        db.session.execute(
            delete(Publication)
            .where(Publication.id.in_(pubs_without_catalog))
        )

        db.session.commit()


class AutoFillFolders(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "AutoFillFolders",
    }

    def __init__(self):
        super().__init__(
            scheduled=datetime.now(timezone.utc),
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='1',
        )

    def _run_actual(self):
        for f in db.session.execute(
            select(Folder)
            .where(Folder.autofill_year != None)
        ).scalars():
            self._add_publications_to_folder(f)

        db.session.commit()

    def _add_publications_to_folder(self, folder: Folder):
        bcp = best_catalog_publications()
        autofill_start = date(folder.autofill_year, 4, 1)
        autofill_end = date(folder.autofill_year + 1, 3, 31)

        for cp in db.session.execute(
            select(CatalogPublication)
            .select_from(CatalogPublication)
            .join(CatalogPublication.publication)
            .where(CatalogPublication.id.in_(bcp))
            .where(CatalogPublication.doi.not_in(
                select(FolderDoi.doi)
                .where(FolderDoi.folder_id == folder.id)
            ))
            .where(CatalogPublication.doi.not_in(
                select(FolderExcludedDoi.doi)
                .where(FolderExcludedDoi.folder_id == folder.id)
            ))
            .where(CatalogPublication.publication_period_start <= autofill_end)
            .where(CatalogPublication.publication_period_end >= autofill_start)
            .where(CatalogPublication.doi != None)
        ).scalars():
            db.session.add(FolderDoi(
                folder_id=folder.id,
                doi=cp.doi,
            ))