import logging
from sqlalchemy import select
from academics.catalogs.data_classes import CatalogReference
from lbrc_flask.database import db
from academics.model.academic import AcademicPotentialSource, Source


def get_sources_for_catalog_identifiers(catalog, catalog_identifiers):
    return [
        get_or_create_source(catalog=catalog, catalog_identifier=ci)
        for ci in catalog_identifiers
    ]


def create_potential_sources(sources, academic, not_match=True):
    logging.warning('1'*20)
    existing_sources = {CatalogReference(s.source) for s in db.session.execute(
        select(AcademicPotentialSource)
        .where(AcademicPotentialSource.academic == academic)
    ).scalars()}

    logging.warning('2'*20)
    for s in sources:
        s.academic = academic

    logging.warning('3'*20)
    potentials = [
        AcademicPotentialSource(academic=academic, source=s, not_match=not_match)
        for s in sources
        if CatalogReference(s) not in existing_sources
    ]

    logging.warning('4'*20)
    db.session.add_all(sources)
    db.session.add_all(potentials)

    logging.warning('5'*20)
    db.session.commit()
    logging.warning('6'*20)


def get_or_create_source(catalog, catalog_identifier):
    result = db.session.execute(
        select(Source)
        .where(Source.catalog == catalog)
        .where(Source.catalog_identifier == catalog_identifier)
    ).unique().scalar()

    if not result:
        result = Source(
            catalog=catalog,
            catalog_identifier=catalog_identifier,
        )

    return result
