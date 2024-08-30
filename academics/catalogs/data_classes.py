import logging
from dataclasses import dataclass
from itertools import chain, groupby
from sqlalchemy import select
from academics.model.academic import Affiliation, Source
from academics.model.catalog import CATALOG_SCIVAL
from academics.model.institutions import Institution
from academics.model.publication import CatalogPublication, Journal, Keyword, Publication, Sponsor, Subtype
from lbrc_flask.database import db
from datetime import date
from unidecode import unidecode

from academics.model.raw_data import RawData


@dataclass(init=False, unsafe_hash=True)
class CatalogReference():
    catalog: str
    catalog_identifier: str

    def __init__(self, catalog_item):
        self.catalog = catalog_item.catalog.lower().strip()
        self.catalog_identifier = catalog_item.catalog_identifier.lower().strip()


@dataclass
class AuthorData():
    catalog: str
    catalog_identifier: str
    orcid: str
    first_name: str
    last_name: str
    initials: str
    href: str
    affiliations: list
    author_name: str = None
    citation_count: str = None
    document_count: str = None
    h_index: str = None
    raw_text: str = None
    action: str = None

    @property
    def display_name(self):
        if self.author_name:
            return self.author_name
        else:
            return ' '.join(filter(None, [self.first_name, self.last_name]))

    @property
    def is_local(self):
        return any([a.is_local for a in self.affiliations])

    @property
    def affiliation_summary(self):
        return '; '.join(a.summary for a in self.affiliations)

    def get_new_source(self):
        result = Source()
        self.update_source(result)

        return result

    def update_source(self, source):
        source.catalog_identifier = self.catalog_identifier
        source.catalog = self.catalog
        source.type = self.catalog
        source.orcid = self.orcid
        source.first_name = self.first_name
        source.last_name = self.last_name
        source.initials = self.initials
        source.display_name = self.display_name
        source.href = self.href
        source.citation_count = self.citation_count
        source.document_count = self.document_count
        source.h_index = self.h_index


@dataclass
class PublicationData():
    catalog: str
    catalog_identifier: str
    href: str
    doi: str
    title: str
    journal_name: str
    publication_cover_date: date
    abstract_text: str
    funding_list: set
    funding_text: str
    volume: str
    issue: str
    pages: str
    subtype_code: str
    subtype_description: str
    cited_by_count: int
    authors: list
    keywords: str
    is_open_access : bool = False
    raw_text: str = None
    action: str = None
    publication_year: str = None
    publication_month: str = None
    publication_day: str = None
    publication_date_text: str = None


@dataclass
class AffiliationData():
    catalog: str
    catalog_identifier: str
    name: str = ''
    address: str = ''
    country: str = ''
    raw_text: str = None
    action: str = None

    @property
    def is_local(self):
        return 'leicester' in self.summary.lower() or 'loughborough' in self.summary.lower() or 'northampton' in self.summary.lower()

    @property
    def summary(self):
        return ', '.join(filter(None, [self.name, self.address, self.country]))

    def update_affiliation(self, affiliation):
        affiliation.catalog_identifier = self.catalog_identifier
        affiliation.catalog = self.catalog
        affiliation.name = self.name
        affiliation.address = self.address
        affiliation.country = self.country


@dataclass
class InstitutionData():
    catalog: str
    catalog_identifier: str
    name: str = ''
    country_code: str = ''
    sector: str = ''
    raw_text: str = None
    action: str = None

    def update_institution(self, institution):
        institution.catalog_identifier = self.catalog_identifier
        institution.catalog = self.catalog
        institution.name = self.name
        institution.country_code = self.country_code
        institution.sector = self.sector

        return institution


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

    cat_pubs_no_pub = (pd for pd in publication_datas if CatalogReference(pd) not in xref.keys() and pd.doi)
    dois_for_cat_pubs_no_pubs = {pd.doi for pd in cat_pubs_no_pub}
    new_pubs = {doi: Publication(doi=doi, refresh_full_details=True) for doi in dois_for_cat_pubs_no_pubs}

    db.session.add_all(new_pubs.values())
    db.session.commit()

    xref = xref | {CatalogReference(pd): new_pubs[pd.doi] for pd in cat_pubs_no_pub}

    return {CatalogReference(p): xref[CatalogReference(p)] for p in publication_datas}


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
        new_i.refresh_full_details = True

        xref[new_i.catalog_identifier] = new_i

        db.session.add(new_i)
        db.session.add(RawData(
            catalog=i.catalog,
            catalog_identifier=i.catalog_identifier,
            action=i.action,
            raw_text=i.raw_text,
        ))
    
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
                refresh_details=True,
            ))
            db.session.add(RawData(
                catalog=a.catalog,
                catalog_identifier=a.catalog_identifier,
                action=a.action,
                raw_text=a.raw_text,
            ))

        db.session.add_all(new_affiliations)
        db.session.commit()

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

        logging.warn('B'*100)

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
