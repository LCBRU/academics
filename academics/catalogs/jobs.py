from datetime import datetime, timezone
from itertools import groupby
import logging
from lbrc_flask.async_jobs import AsyncJob, AsyncJobs
from lbrc_flask.database import db
from sqlalchemy import delete, select
from academics.services.sources import create_potential_sources
from academics.catalogs.data_classes import CatalogReference
from academics.catalogs.open_alex import get_open_alex_affiliation_data, get_open_alex_author_data, get_open_alex_publication_data, get_openalex_publications, open_alex_similar_authors
from academics.catalogs.publication import _affiliation_xref_for_author_data_list, _institutions, _source_xref_for_author_data_list, save_publications
from academics.catalogs.scival import get_scival_institution, get_scival_publication_institutions
from academics.catalogs.scopus import get_scopus_affiliation_data, get_scopus_author_data, get_scopus_publication_data, get_scopus_publications, scopus_similar_authors
from academics.model.academic import Academic, AcademicPotentialSource, Affiliation, Source
from academics.model.catalog import CATALOG_OPEN_ALEX, CATALOG_SCIVAL, CATALOG_SCOPUS
from academics.model.folder import FolderDoi
from academics.model.institutions import Institution
from academics.model.publication import CatalogPublication, NihrAcknowledgement, Publication


class RefreshAll(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "RefreshAll",
    }

    def __init__():
        super.__init__(
            scheduled=datetime.now(timezone.utc),
            retry=False,
        )

    def _run_actual(self):
        for academic in db.session.execute(select(Academic)).scalars():
            AsyncJobs.schedule(AcademicRefresh(academic))

        AsyncJobs.schedule(PublicationRemoveUnused)


class AffiliationRefresh(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "AffiliationRefresh",
    }

    def __init__(affiliation):
        db.session.refresh(affiliation)
        super.__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=affiliation.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='7',
        )

    def _run_actual(self):
        affiliation = db.session.execute(select(Affiliation).where(Affiliation.id == self.entity_id)).scalar()
        
        if affiliation.catalog == CATALOG_SCOPUS:
            aff_data = get_scopus_affiliation_data(affiliation.catalog_identifier)
        if affiliation.catalog == CATALOG_OPEN_ALEX:
            aff_data = get_open_alex_affiliation_data(affiliation.catalog_identifier)

        aff_data.update_affiliation(affiliation)

        db.session.add(affiliation)
        db.session.commit()


class InstitutionRefresh(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "InstitutionRefresh",
    }

    def __init__(institution):
        db.session.refresh(institution)
        super.__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=institution.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='7',
        )

    def _run_actual(self):
        institution = db.session.execute(select(Institution).where(Institution.id == self.entity_id)).scalar()
        
        if institution.catalog != CATALOG_SCIVAL:
            raise Exception(f'What?! Institution catalog is {institution.catalog}')

        institution_data = get_scival_institution(institution.catalog_identifier)

        if not institution_data:
            logging.warning(f'Institution not found {institution.catalog_identifier}')

        institution_data.update_institution(institution)

        db.session.add(institution)
        db.session.commit()


class PublicationGetMissingScopus(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "PublicationGetMissingScopus",
    }

    def __init__(publication):
        db.session.refresh(publication)
        super.__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=publication.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='14',
        )

    def _run_actual(self):
        publication = db.session.execute(select(Publication).where(Publication.id == self.entity_id)).scalar()
        if not publication.scopus_catalog_publication and publication.doi:
            if pub_data := get_scopus_publication_data(doi=publication.doi):
                save_publications([pub_data])


class PublicationGetScivalInstitutions(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "PublicationGetScivalInstitutions",
    }

    def __init__(publication):
        db.session.refresh(publication)
        super.__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=publication.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='14',
        )

    def _run_actual(self):
        publication = db.session.execute(select(Publication).where(Publication.id == self.entity_id)).scalar()
        if publication.scopus_catalog_publication and not publication.institutions:
            institutions = get_scival_publication_institutions(publication.scopus_catalog_publication.catalog_identifier)
            publication.institutions = set(_institutions(institutions))


class PublicationInitialise(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "PublicationInitialise",
    }

    def __init__(publication):
        db.session.refresh(publication)
        super.__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=publication.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='1',
        )

    def _run_actual(self):
        publication: Publication = db.session.execute(select(Publication).where(Publication.id == self.entity_id)).scalar()
        publication.set_vancouver()

        if publication.best_catalog_publication.journal and publication.best_catalog_publication.journal.preprint and publication.preprint is None:
            publication.preprint = True

        if publication.is_nihr_acknowledged and publication.auto_nihr_acknowledgement is None and publication.nihr_acknowledgement is None:
            publication.nihr_acknowledgement = publication.auto_nihr_acknowledgement = NihrAcknowledgement.get_acknowledged_status()

        if publication.scopus_catalog_publication is None:
            AsyncJobs.schedule(PublicationGetMissingScopus(publication))
        AsyncJobs.schedule(PublicationGetScivalInstitutions(publication))


class CatalogPublicationRefresh(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "CatalogPublicationRefresh",
    }

    def __init__(catalog_publication):
        db.session.refresh(catalog_publication)
        super.__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=catalog_publication.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='1',
        )

    def _run_actual(self):
        catalog_publication = db.session.execute(select(CatalogPublication).where(CatalogPublication.id == self.entity_id)).scalar()
        pub_data = None
        if catalog_publication.catalog == CATALOG_SCOPUS:
            pub_data = get_scopus_publication_data(scopus_id=catalog_publication.catalog_identifier)
        if catalog_publication.catalog == CATALOG_OPEN_ALEX:
            pub_data = get_open_alex_publication_data(catalog_publication.catalog_identifier)

        if pub_data:
            save_publications([pub_data])

        db.session.add(catalog_publication)
        db.session.commit()


class SourceRefresh(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "SourceRefresh",
    }

    def __init__(source):
        db.session.refresh(source)
        super.__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=source.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='1',
        )

    def _run_actual(self):
        source = db.session.execute(select(Source).where(Source.id == self.entity_id)).scalar()
        author_data = None

        if source.catalog == CATALOG_SCOPUS:
            author_data = get_scopus_author_data(source.catalog_identifier)
        if source.catalog == CATALOG_OPEN_ALEX:
            author_data = get_open_alex_author_data(source.catalog_identifier)

        if author_data and CatalogReference(source) == CatalogReference(author_data):
            _source_xref_for_author_data_list([author_data])
            affiliation_xref = _affiliation_xref_for_author_data_list([author_data])

            if CatalogReference(source) in affiliation_xref:
                source.affiliations = affiliation_xref[CatalogReference(source)]

            author_data.update_source(source)
        else:
            logging.warn(f'Source {source.display_name} not found so setting it to be in error')
            source.error = True

        db.session.add(source)
        AsyncJobs.schedule(SourceGetPublications(source))
        db.session.commit()


class SourceGetPublications(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "SourceGetPublications",
    }

    def __init__(source):
        db.session.refresh(source)
        super.__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=source.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='1',
        )

    def _run_actual(self):
        source = db.session.execute(select(Source).where(Source.id == self.entity_id)).scalar()
        if not source.academic:
            return

        publication_datas = []

        if source.catalog == CATALOG_SCOPUS:
            publication_datas = get_scopus_publications(source.catalog_identifier)
        if source.catalog == CATALOG_OPEN_ALEX:
            publication_datas = get_openalex_publications(source.catalog_identifier)

        existing = set()

        keyfunc = lambda a: a.catalog

        for cat, pubs in groupby(sorted(publication_datas, key=keyfunc), key=keyfunc):
            q = select(CatalogPublication).where(
                CatalogPublication.catalog_identifier.in_(p.catalog_identifier for p in pubs)
            ).where(
                CatalogPublication.catalog == cat
            )

            existing = existing | {CatalogReference(cp) for cp in db.session.execute(q).unique().scalars()}

        new_pubs = [p for p in publication_datas if CatalogReference(p) not in existing]

        save_publications(new_pubs)

        source.last_fetched_datetime = datetime.now(timezone.utc)

        db.session.add(source)
        db.session.commit()


class AcademicInitialise(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "AcademicInitialise",
    }

    def __init__(academic):
        db.session.refresh(academic)
        super.__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=academic.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='1',
        )

    def _run_actual(self):
        academic = db.session.execute(select(Academic).where(Academic.id == self.entity_id)).scalar()
        academic.ensure_initialisation()
        academic.updating = False
        academic.initialised = True
        db.session.add(academic)
        db.session.commit()


class AcademicRefresh(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "AcademicInitialise",
    }

    def __init__(academic):
        db.session.refresh(academic)
        super.__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=academic.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='1',
        )

    def _run_actual(self):
        academic = db.session.execute(select(Academic).where(Academic.id == self.entity_id)).scalar()

        AsyncJobs.schedule(AcademicFindNewPotentialSources(academic))
        AsyncJobs.schedule(AcademicEnsureSourcesArePotential(academic))

        for s in academic.sources:
            AsyncJobs.schedule(SourceRefresh(s))
            AsyncJobs.schedule(SourceGetPublications(s))


class AcademicFindNewPotentialSources(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "AcademicFindNewPotentialSources",
    }

    def __init__(academic):
        db.session.refresh(academic)
        super.__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=academic.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='1',
        )

    def _run_actual(self):
        academic = db.session.execute(select(Academic).where(Academic.id == self.entity_id)).scalar()

        if len(academic.last_name.strip()) < 1:
            return

        new_source_datas = filter(
            lambda s: s.is_local,
            [*scopus_similar_authors(academic), *open_alex_similar_authors(academic)],
        )

        affiliation_xref = _affiliation_xref_for_author_data_list(new_source_datas)
        new_sources = _source_xref_for_author_data_list(new_source_datas).values()

        for s in new_sources:
            s.affiliations = affiliation_xref[CatalogReference(s)]

        create_potential_sources(new_sources, academic, not_match=True)


class AcademicEnsureSourcesArePotential(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "AcademicEnsureSourcesArePotential",
    }

    def __init__(academic):
        db.session.refresh(academic)
        super.__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=academic.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='1',
        )

    def _run_actual(self):
        academic = db.session.execute(select(Academic).where(Academic.id == self.entity_id)).scalar()

        missing_proposed_sources = list(db.session.execute(
            select(Source)
            .where(~Source.potential_academics.any())
            .where(Source.academic == academic)
        ).scalars())

        logging.debug(f'Missing proposed sources found: {missing_proposed_sources}')

        for source in missing_proposed_sources:
            aps = AcademicPotentialSource(
                academic=academic,
                source=source,
            )

            db.session.add(aps)
        
        db.session.commit()


class PublicationRemoveUnused(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "PublicationRemoveUnused",
    }

    def __init__():
        super.__init__(
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
