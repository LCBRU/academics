from sqlalchemy import select
from academics.catalogs.data_classes import CatalogReference
from lbrc_flask.database import db

from academics.catalogs.service import schedule_source_update
from academics.model.academic import AcademicPotentialSource, Source


def add_sources_to_academic(catalog, catalog_identifiers, academic):
    sources = [
        get_or_create_source(catalog=catalog, catalog_identifier=ci)
        for ci in catalog_identifiers
    ]

    create_potential_sources(sources, academic, not_match=False)

    for s in sources:
        schedule_source_update(s)

    db.session.commit()


def create_potential_sources(sources, academic, not_match=True):
    existing_sources = {CatalogReference(s.source) for s in db.session.execute(
        select(AcademicPotentialSource)
        .where(AcademicPotentialSource.academic == academic)
    ).scalars()}

    for s in sources:
        s.academic = academic

    potentials = [
        AcademicPotentialSource(academic=academic, source=s, not_match=not_match)
        for s in sources
        if CatalogReference(s) not in existing_sources
    ]

    db.session.add_all(sources)
    db.session.add_all(potentials)
    db.session.commit()


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
