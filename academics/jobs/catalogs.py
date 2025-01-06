import logging
from datetime import date, datetime, timezone
from dateutil.relativedelta import relativedelta
from unidecode import unidecode
from itertools import chain, groupby
from lbrc_flask.async_jobs import AsyncJob, AsyncJobs
from lbrc_flask.database import db
from flask import current_app
from sqlalchemy import delete, select
from academics.services.sources import create_potential_sources
from academics.catalogs.data_classes import CatalogReference
from academics.catalogs.open_alex import get_open_alex_affiliation_data, get_open_alex_author_data, get_open_alex_publication_data, get_openalex_publications, open_alex_similar_authors
from academics.catalogs.scival import get_scival_institution, get_scival_publication_institutions
from academics.catalogs.scopus import get_scopus_affiliation_data, get_scopus_author_data, get_scopus_publication_data, get_scopus_publications, scopus_similar_authors
from academics.model.academic import Academic, AcademicPotentialSource, Affiliation, Source, CatalogPublicationsSources, catalog_publications_sources_affiliations, Affiliation, Source
from academics.model.catalog import CATALOG_OPEN_ALEX, CATALOG_SCIVAL, CATALOG_SCOPUS
from academics.model.institutions import Institution
from academics.model.publication import CatalogPublication, NihrAcknowledgement, Journal, Keyword, Publication, Sponsor, Subtype
from lbrc_flask.validators import parse_date
from academics.model.raw_data import RawData


def _journal_xref_for_publication_data_list(publication_datas):
    logging.debug('started')

    unique_names = {unidecode(p.journal_name).lower() for p in publication_datas}

    q = select(Journal.id, Journal.name).where(Journal.name.in_(unique_names))

    xref = {unidecode(j['name']).lower(): j['id'] for j in db.session.execute(q).mappings()}

    new_journals = [Journal(name=n) for n in unique_names if unidecode(n).lower() not in xref.keys()]

    db.session.add_all(new_journals)
    db.session.commit()

    xref = xref | {j.name.lower(): j.id for j in new_journals}

    return {CatalogReference(p): xref[unidecode(p.journal_name).lower()] for p in publication_datas}


def _subtype_xref_for_publication_data_list(publication_datas):
    logging.debug('started')

    descs = {p.subtype_description for p in publication_datas}

    q = select(Subtype.id, Subtype.description).where(Subtype.description.in_(descs))

    xref = {st['description'].lower(): st['id'] for st in db.session.execute(q).mappings()}

    new_subtypes = [Subtype(code=d, description=d) for d in descs if d.lower() not in xref.keys()]

    db.session.add_all(new_subtypes)
    db.session.commit()

    xref = xref | {st.description.lower(): st.id for st in new_subtypes}

    return {CatalogReference(p): xref[p.subtype_description.lower()] for p in publication_datas}


def _publication_xref_for_publication_data_list(publication_datas):
    logging.debug('started')

    xref = {}

    keyfunc = lambda a: a.catalog

    for cat, pubs in groupby(sorted(publication_datas, key=keyfunc), key=keyfunc):
        q = select(CatalogPublication).where(
            CatalogPublication.catalog_identifier.in_([p.catalog_identifier for p in pubs])
        ).where(
            CatalogPublication.catalog == cat
        ).distinct()

        xref = xref | {CatalogReference(cp): cp.publication for cp in db.session.execute(q).unique().scalars()}

    for p in (p for p in publication_datas if CatalogReference(p) not in xref.keys() and p.doi):
        if pub := db.session.execute(
            select(Publication).where(Publication.doi == p.doi)
        ).unique().scalar_one_or_none():
            xref[CatalogReference(p)] = pub

    xref = xref | _publication_xref_for_pub_data_with_doi([pd for pd in publication_datas if CatalogReference(pd) not in xref.keys() and pd.doi])
    xref = xref | _publication_xref_for_pub_data_with_no_doi([pd for pd in publication_datas if CatalogReference(pd) not in xref.keys()])

    return {CatalogReference(p): xref[CatalogReference(p)] for p in publication_datas}


def _publication_xref_for_pub_data_with_doi(pub_data):
    dois_for_cat_pubs_no_pubs = {pd.doi for pd in pub_data}
    new_pubs = {doi: Publication(doi=doi, refresh_full_details=True) for doi in dois_for_cat_pubs_no_pubs}

    for np in new_pubs.values():
        db.session.add(np)
        db.session.commit()
        AsyncJobs.schedule(PublicationInitialise(np))

    return {CatalogReference(pd): new_pubs[pd.doi] for pd in pub_data}
    

def _publication_xref_for_pub_data_with_no_doi(pub_data):
    result = {}

    for pd in pub_data:
        new_pub = Publication(refresh_full_details=True)
        db.session.add(new_pub)
        db.session.commit()
        AsyncJobs.schedule(PublicationInitialise(new_pub))
        result[CatalogReference(pd)] = new_pub

    return result
    

def _sponsor_xref_for_publication_data_list(publication_datas):
    logging.debug('started')

    unique_names = set(filter(None, [n for n in chain.from_iterable([p.funding_list for p in publication_datas])]))
    unique_names = set([unidecode(n).lower() for n in unique_names])

    q = select(Sponsor).where(Sponsor.name.in_(unique_names))

    xref = {unidecode(s.name).lower(): s for s in db.session.execute(q).scalars()}

    new_sponsors = [Sponsor(name=u) for u in unique_names if u not in xref.keys()]

    db.session.add_all(new_sponsors)
    db.session.commit()

    xref = xref | {unidecode(s.name).lower(): s for s in new_sponsors}

    return {
        CatalogReference(p): [xref[unidecode(n).lower()] for n in p.funding_list if n]
        for p in publication_datas
    }


def _institutions(institution_datas):
    logging.debug('started')

    q = select(Institution).where(
        Institution.catalog_identifier.in_([i.catalog_identifier for i in institution_datas])
    ).where(Institution.catalog == CATALOG_SCIVAL)

    xref = {i.catalog_identifier: i for i in db.session.execute(q).scalars()}

    for i in institution_datas:
        if str(i.catalog_identifier) in xref.keys():
            continue

        new_i = Institution()
        i.update_institution(new_i)

        xref[new_i.catalog_identifier] = new_i

        db.session.add(new_i)
        db.session.add(RawData(
            catalog=i.catalog,
            catalog_identifier=i.catalog_identifier,
            action=i.action,
            raw_text=i.raw_text,
        ))
        db.session.commit()
        AsyncJobs.schedule(InstitutionRefresh(new_i))
    
    db.session.commit()

    return xref.values()


def _keyword_xref_for_publication_data_list(publication_datas):
    logging.debug('started')

    unique_keywords = {unidecode(k.strip()).lower() for k in chain.from_iterable([p.keywords for p in publication_datas]) if k}

    q = select(Keyword).where(Keyword.keyword.in_(unique_keywords))

    xref = {unidecode(k.keyword).lower(): k for k in db.session.execute(q).scalars()}

    new_keywords = [Keyword(keyword=u) for u in unique_keywords if u not in xref.keys()]

    db.session.add_all(new_keywords)
    db.session.commit()

    xref = xref | {unidecode(k.keyword).lower(): k for k in new_keywords}

    return {
        CatalogReference(p): [xref[unidecode(k.strip()).lower()] for k in p.keywords if k]
        for p in publication_datas
    }


def _affiliation_xref_for_author_data_list(author_datas):
    logging.debug('started')

    author_datas = list(author_datas)

    affiliations = {CatalogReference(af): af for af in chain.from_iterable([a.affiliations for a in author_datas])}

    xref = {}

    keyfunc = lambda a: a.catalog

    for cat, afils in groupby(sorted(affiliations.values(), key=keyfunc), key=keyfunc):

        afils = list(afils)

        q = select(Affiliation).where(
            Affiliation.catalog_identifier.in_([a.catalog_identifier for a in afils])
        ).where(
            Affiliation.catalog == cat
        )

        xref = xref | {CatalogReference(a): a for a in db.session.execute(q).scalars()}

        new_affiliations = []

        for a in afils:
            if CatalogReference(a) in xref.keys():
                continue

            new_affiliations.append(Affiliation(
                catalog=cat,
                catalog_identifier=a.catalog_identifier,
                name=a.name,
                address=a.address,
                country=a.country,
            ))
            db.session.add(RawData(
                catalog=a.catalog,
                catalog_identifier=a.catalog_identifier,
                action=a.action,
                raw_text=a.raw_text,
            ))

        db.session.add_all(new_affiliations)
        db.session.commit()

        for a in new_affiliations:
            AsyncJobs.schedule(AffiliationRefresh(a))

        xref = xref | {CatalogReference(a): a for a in new_affiliations}

    results = {}

    for a in author_datas:
        results[CatalogReference(a)] = [xref[af] for af in {CatalogReference(af) for af in a.affiliations}]

    return results


def _source_xref_for_publication_data_list(publication_datas):
    logging.debug('started')

    authors = {CatalogReference(a): a for a in chain.from_iterable([p.authors for p in publication_datas])}

    author_xref = _source_xref_for_author_data_list(authors.values())

    return {
        CatalogReference(p): [author_xref[CatalogReference(a)] for a in p.authors]
        for p in publication_datas
    }


def _source_xref_for_author_data_list(author_datas):
    logging.debug('started')

    xref = {}

    keyfunc = lambda a: a.catalog

    for cat, authors in groupby(sorted(author_datas, key=keyfunc), key=keyfunc):
        q = select(Source).where(
            Source.catalog_identifier.in_([a.catalog_identifier for a in authors])
        ).where(
            Source.catalog == cat
        )

        xref = xref | {CatalogReference(a): a for a in db.session.execute(q).scalars()}

    new_sources = []

    for a in author_datas:
        if CatalogReference(a) in xref.keys():
            continue

        new_sources.append(a.get_new_source())
        db.session.add(RawData(
            catalog=a.catalog,
            catalog_identifier=a.catalog_identifier,
            action=a.action,
            raw_text=a.raw_text,
        ))

    db.session.add_all(new_sources)
    db.session.commit()

    return xref | {CatalogReference(s): s for s in new_sources}


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

        AsyncJobs.schedule(CatalogPublicationRefresh(cat_pub))

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


class RefreshAll(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "RefreshAll",
    }

    def __init__(self):
        super().__init__(
            scheduled=datetime.now(timezone.utc),
            retry=False,
        )

    def _run_actual(self):
        for academic in db.session.execute(select(Academic)).scalars():
            AsyncJobs.schedule(AcademicRefresh(academic))



class AffiliationRefresh(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "AffiliationRefresh",
    }

    def __init__(self, affiliation):
        db.session.refresh(affiliation)
        super().__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=affiliation.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='7',
        )

    def _run_actual(self):
        affiliation = db.session.execute(select(Affiliation).where(Affiliation.id == self.entity_id)).scalar_one_or_none()

        if not affiliation:
            return
        
        if affiliation.catalog == CATALOG_SCOPUS:
            aff_data = get_scopus_affiliation_data(affiliation.catalog_identifier)
        if affiliation.catalog == CATALOG_OPEN_ALEX:
            aff_data = get_open_alex_affiliation_data(affiliation.catalog_identifier)

        aff_data.update_affiliation(affiliation)

        db.session.add(affiliation)
        db.session.commit()


class InstitutionRefreshAll(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "InstitutionRefreshAll",
    }

    def __init__(self):
        super().__init__(
            scheduled=datetime.now(timezone.utc),
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='7',
        )

    def _run_actual(self):
        insts: list[Institution] = db.session.execute(
            select(Institution)
        ).scalars()

        for i in insts:
            AsyncJobs.schedule(InstitutionRefresh(i))


class InstitutionRefresh(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "InstitutionRefresh",
    }

    def __init__(self, institution):
        db.session.refresh(institution)
        super().__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=institution.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='7',
        )

    def _run_actual(self):
        institution = db.session.execute(select(Institution).where(Institution.id == self.entity_id)).scalar_one_or_none()

        if not institution:
            return
        
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

    def __init__(self, publication):
        db.session.refresh(publication)
        super().__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=publication.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='14',
        )

    def _run_actual(self):
        publication = db.session.execute(select(Publication).where(Publication.id == self.entity_id)).scalar_one_or_none()

        if not publication:
            return

        if not publication.scopus_catalog_publication and publication.doi:
            if pub_data := get_scopus_publication_data(doi=publication.doi):
                save_publications([pub_data])


class PublicationGetScivalInstitutions(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "PublicationGetScivalInstitutions",
    }

    def __init__(self, publication):
        db.session.refresh(publication)
        super().__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=publication.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='14',
        )

    def _run_actual(self):
        publication = db.session.execute(select(Publication).where(Publication.id == self.entity_id)).scalar_one_or_none()
        if not publication:
            return

        if publication.scopus_catalog_publication and not publication.institutions:
            institutions = get_scival_publication_institutions(publication.scopus_catalog_publication.catalog_identifier)
            publication.institutions = set(_institutions(institutions))


class PublicationInitialise(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "PublicationInitialise",
    }

    def __init__(self, publication):
        db.session.refresh(publication)
        super().__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=publication.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='1',
        )

    def _run_actual(self):
        publication: Publication = db.session.execute(select(Publication).where(Publication.id == self.entity_id)).scalar_one_or_none()
        if not publication:
            return

        publication.set_vancouver()
        publication.set_preprint_from_guess()
        publication.set_status_from_guess()

        db.session.add(publication)
        db.session.commit()

        if publication.scopus_catalog_publication is None:
            AsyncJobs.schedule(PublicationGetMissingScopus(publication))
        AsyncJobs.schedule(PublicationGetScivalInstitutions(publication))


class PublicationReGuessStatus(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "PublicationReGuessStatus",
    }

    def __init__(self):
        super().__init__(
            scheduled=datetime.now(timezone.utc),
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='1',
        )

    def _run_actual(self):
        pubs: list[Publication] = db.session.execute(
            select(Publication)
            .where(Publication.id.in_(
                select(CatalogPublication.publication_id)
                .where(CatalogPublication.publication_cover_date > '2024-04-01')
            ))
            .where(Publication.nihr_acknowledgement_id == None)
        ).scalars()

        i = 0
        for p in pubs:
            if p.is_supplementary:
                i = i + 1
                print(f'==== doing {i}  ====')
                p.auto_nihr_acknowledgement_id = p.nihr_acknowledgement_id = NihrAcknowledgement.get_supplementary_status().id
                db.session.add(p)
        db.session.commit()


class CatalogPublicationRefresh(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "CatalogPublicationRefresh",
    }

    def __init__(self, catalog_publication):
        db.session.refresh(catalog_publication)
        super().__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=catalog_publication.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='1',
        )

    def _run_actual(self):
        catalog_publication = db.session.execute(select(CatalogPublication).where(CatalogPublication.id == self.entity_id)).scalar_one_or_none()
        if not catalog_publication:
            return

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

    def __init__(self, source):
        db.session.refresh(source)
        super().__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=source.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='1',
        )

    def _run_actual(self):
        source = db.session.execute(select(Source).where(Source.id == self.entity_id)).scalar_one_or_none()
        if not source:
            return

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
            logging.warning(f'Source {source.display_name} not found so setting it to be in error')
            source.error = True

        db.session.add(source)
        db.session.commit()
        AsyncJobs.schedule(SourceGetPublications(source))


class SourceGetPublications(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "SourceGetPublications",
    }

    def __init__(self, source):
        db.session.refresh(source)
        super().__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=source.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='1',
        )

    def _run_actual(self):
        source = db.session.execute(select(Source).where(Source.id == self.entity_id)).scalar_one_or_none()
        if not source or not source.academic:
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

    def __init__(self, academic):
        db.session.refresh(academic)
        super().__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=academic.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='1',
        )

    def _run_actual(self):
        academic = db.session.execute(select(Academic).where(Academic.id == self.entity_id)).scalar_one_or_none()
        if not academic:
            return
        
        academic.ensure_initialisation()
        academic.updating = False
        academic.initialised = True
        db.session.add(academic)
        db.session.commit()


class AcademicRefresh(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "AcademicRefresh",
    }

    def __init__(self, academic):
        db.session.refresh(academic)
        super().__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=academic.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='1',
        )

    def _run_actual(self):
        academic = db.session.execute(select(Academic).where(Academic.id == self.entity_id)).scalar_one_or_none()
        if not academic:
            return

        AsyncJobs.schedule(AcademicFindNewPotentialSources(academic))
        AsyncJobs.schedule(AcademicEnsureSourcesArePotential(academic))

        for s in academic.sources:
            AsyncJobs.schedule(SourceRefresh(s))
            AsyncJobs.schedule(SourceGetPublications(s))


class AcademicFindNewPotentialSources(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "AcademicFindNewPotentialSources",
    }

    def __init__(self, academic):
        db.session.refresh(academic)
        super().__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=academic.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='1',
        )

    def _run_actual(self):
        academic = db.session.execute(select(Academic).where(Academic.id == self.entity_id)).scalar_one_or_none()
        if not academic:
            return

        if len(academic.last_name.strip()) < 1:
            return

        new_source_datas = list(filter(
            lambda s: s.is_local,
            [*scopus_similar_authors(academic), *open_alex_similar_authors(academic)],
        ))

        affiliation_xref = _affiliation_xref_for_author_data_list(new_source_datas)
        new_sources = _source_xref_for_author_data_list(new_source_datas).values()

        for s in new_sources:
            s.affiliations = affiliation_xref[CatalogReference(s)]

        create_potential_sources(new_sources, academic, not_match=True)


class AcademicEnsureSourcesArePotential(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "AcademicEnsureSourcesArePotential",
    }

    def __init__(self, academic):
        db.session.refresh(academic)
        super().__init__(
            scheduled=datetime.now(timezone.utc),
            entity_id=academic.id,
            retry=True,
            retry_timedelta_period='days',
            retry_timedelta_size='1',
        )

    def _run_actual(self):
        academic = db.session.execute(select(Academic).where(Academic.id == self.entity_id)).scalar_one_or_none()
        if not academic:
            return

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
