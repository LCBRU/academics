from datetime import datetime
from sqlalchemy import select
from lbrc_flask.database import db
from lbrc_flask.async_jobs import AsyncJobs
from academics.jobs.catalogs import CatalogPublicationRefresh
from academics.model.catalog import CATALOG_MANUAL
from academics.model.publication import CatalogPublication, Publication


def update_manual_publication(catalog_publication, doi, title=None, publication_cover_date=None):
    publication = db.session.execute(
            select(Publication)
            .where(Publication.doi == doi)
        ).unique().scalar_one_or_none() or Publication(doi=doi, refresh_full_details=True)

    catalog_publication.catalog_identifier = doi
    catalog_publication.doi = doi
    catalog_publication.title = title or ''
    catalog_publication.publication_cover_date = publication_cover_date or datetime.now()
    catalog_publication.abstract = ''
    catalog_publication.volume = ''
    catalog_publication.issue = ''
    catalog_publication.pages = ''
    catalog_publication.funding_text = ''
    catalog_publication.href = ''
    catalog_publication.refresh_full_details = True
    catalog_publication.publication = publication

    db.session.add(catalog_publication)
    db.session.flush()

    AsyncJobs.schedule(CatalogPublicationRefresh(catalog_publication))
    db.session.commit()


def add_manual_doi_publications_if_missing(dois):
    existing_dois = set(db.session.execute(
        select(CatalogPublication.doi).where(CatalogPublication.doi.in_(dois))
    ).scalars())
    
    missing_dois = set(dois) - existing_dois

    for doi in missing_dois:
        update_manual_publication(
            catalog_publication=CatalogPublication(catalog=CATALOG_MANUAL),
            doi=doi,
        )