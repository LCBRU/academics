from datetime import date
from itertools import chain
import logging

from flask import current_app
from lbrc_flask.database import db
from sqlalchemy import delete, select
from academics.catalogs.data_classes import CatalogReference, _affiliation_xref_for_author_data_list, _journal_xref_for_publication_data_list, _keyword_xref_for_publication_data_list, _publication_xref_for_publication_data_list, _source_xref_for_publication_data_list, _sponsor_xref_for_publication_data_list, _subtype_xref_for_publication_data_list
from academics.catalogs.jobs import CatalogPublicationRefresh
from academics.model.publication import CatalogPublication
from dateutil.relativedelta import relativedelta
from lbrc_flask.validators import parse_date
from academics.model.raw_data import RawData
from academics.model.publication import CatalogPublication
from academics.model.academic import CatalogPublicationsSources, catalog_publications_sources_affiliations
from lbrc_flask.async_jobs import AsyncJobs


def save_publications(new_pubs):
    logging.info(len(new_pubs))

    journal_xref = _journal_xref_for_publication_data_list(new_pubs)
    subtype_xref = _subtype_xref_for_publication_data_list(new_pubs)
    pubs_xref = _publication_xref_for_publication_data_list(new_pubs)
    sponsor_xref = _sponsor_xref_for_publication_data_list(new_pubs)
    source_xref = _source_xref_for_publication_data_list(new_pubs)
    keyword_xref = _keyword_xref_for_publication_data_list(new_pubs)

    affiliation_xref = _affiliation_xref_for_author_data_list(chain.from_iterable([p.authors for p in new_pubs]))

    for p in new_pubs:
        cpr = CatalogReference(p)
        logging.info(f'Saving Publication {cpr}')

        pub = pubs_xref[cpr]

        cat_pub = db.session.execute(
            select(CatalogPublication)
            .where(CatalogPublication.catalog == p.catalog)
            .where(CatalogPublication.catalog_identifier == p.catalog_identifier)
        ).scalar()

        if not cat_pub:
            cat_pub = CatalogPublication(
                catalog=p.catalog,
                catalog_identifier=p.catalog_identifier,
                refresh_full_details=True,
            )
            AsyncJobs.schedule(CatalogPublicationRefresh(cat_pub))

        cat_pub.publication_id=pub.id
        cat_pub.doi = p.doi or ''
        cat_pub.title = p.title or ''
        cat_pub.publication_cover_date = p.publication_cover_date
        cat_pub.href = p.href
        cat_pub.abstract = p.abstract_text or ''
        cat_pub.funding_text = p.funding_text or ''
        cat_pub.volume = p.volume or ''
        cat_pub.issue = p.issue or ''
        cat_pub.pages = p.pages or ''
        cat_pub.is_open_access = p.is_open_access
        cat_pub.cited_by_count = p.cited_by_count
        cat_pub.journal_id = journal_xref[cpr]
        cat_pub.subtype_id = subtype_xref[cpr]
        cat_pub.sponsors = set(sponsor_xref[cpr])
        cat_pub.keywords = set(keyword_xref[cpr])
        cat_pub.publication_year = p.publication_year
        cat_pub.publication_month = p.publication_month
        cat_pub.publication_day = p.publication_day
        cat_pub.publication_date_text = p.publication_date_text

        if not p.publication_year:
            cat_pub.publication_period_start = cat_pub.publication_period_end = cat_pub.publication_cover_date
        elif p.publication_day:
            cat_pub.publication_period_start = date(year=int(p.publication_year), month=int(p.publication_month), day=int(p.publication_day))
            cat_pub.publication_period_end = cat_pub.publication_period_start
        elif p.publication_month:
            cat_pub.publication_period_start = date(year=int(p.publication_year), month=int(p.publication_month), day=1)
            cat_pub.publication_period_end = cat_pub.publication_period_start + relativedelta(months=1) - relativedelta(days=1)
        else:
            cat_pub.publication_period_start = date(year=int(p.publication_year), month=1, day=1)
            cat_pub.publication_period_end = (cat_pub.publication_period_start + relativedelta(years=1)) - relativedelta(days=1)

        db.session.add(RawData(
            catalog=cat_pub.catalog,
            catalog_identifier=cat_pub.catalog_identifier,
            action=p.action,
            raw_text=p.raw_text,
        ))

        db.session.add(cat_pub)

        pub.validation_historic = (parse_date(p.publication_cover_date) < current_app.config['HISTORIC_PUBLICATION_CUTOFF'])
        db.session.add(pub)

        db.session.commit()

        # When there are lots of sources (authors) for a publication the
        # saving and deleting of these sources (and their associated affiliations)
        # causes SQLAlchemy to fall over, so I've split it up into different bits

        db.session.execute(
            delete(catalog_publications_sources_affiliations)
            .where(CatalogPublicationsSources.id == catalog_publications_sources_affiliations.c.catalog_publications_sources_id)
            .where(CatalogPublicationsSources.catalog_publication_id == cat_pub.id)
        )

        db.session.execute(
            delete(CatalogPublicationsSources)
            .where(CatalogPublicationsSources.catalog_publication_id == cat_pub.id)
        )

        catalog_publication_sources = []

        for i, s in enumerate(source_xref[cpr]):
            cps = CatalogPublicationsSources(
                source=s,
                catalog_publication=cat_pub,
                ordinal=i,
                affiliations=[],
            )
            cps.affiliations_delayed = affiliation_xref[CatalogReference(s)]
            catalog_publication_sources.append(cps)

        db.session.add_all(catalog_publication_sources)
        db.session.commit()

        for c in catalog_publication_sources:
            c.affiliations=c.affiliations_delayed

        db.session.add_all(catalog_publication_sources)
        db.session.commit()
