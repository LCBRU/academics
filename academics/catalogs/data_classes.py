import logging
from dataclasses import dataclass
from itertools import chain, groupby
from sqlalchemy import select
from academics.model.academic import Affiliation, Source
from academics.model.publication import CatalogPublication, Journal, Keyword, Publication, Sponsor, Subtype
from lbrc_flask.database import db
from datetime import date
from unidecode import unidecode


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

    @property
    def display_name(self):
        if self.author_name:
            return self.author_name
        else:
            return ' '.join(filter(None, [self.first_name, self.last_name]))

    @property
    def is_leicester(self):
        return any([a.is_leicester for a in self.affiliations])

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


@dataclass
class AffiliationData():
    catalog: str
    catalog_identifier: str
    name: str = ''
    address: str = ''
    country: str = ''

    @property
    def is_leicester(self):
        return 'leicester' in self.summary.lower()

    @property
    def summary(self):
        return ', '.join(filter(None, [self.name, self.address, self.country]))

    def update_affiliation(self, affiliation):
        affiliation.catalog_identifier = self.catalog_identifier
        affiliation.catalog = self.catalog
        affiliation.name = self.name
        affiliation.address = self.address
        affiliation.country = self.country


def _journal_xref_for_publication_data_list(publication_datas):
    logging.debug('_get_journal_xref: started')

    all_names = {p.journal_name for p in publication_datas}
    unique_names = {unidecode(n).lower(): n for n in all_names}

    q = select(Journal.id, Journal.name).where(Journal.name.in_(unique_names))

    xref = {unidecode(j['name']).lower(): j['id'] for j in db.session.execute(q).mappings()}

    new_journals = [Journal(name=n) for n in unique_names if unidecode(n).lower() not in xref.keys()]

    db.session.add_all(new_journals)
    db.session.commit()

    xref = xref | {j.name.lower(): j.id for j in new_journals}

    return {CatalogReference(p): xref[unidecode(p.journal_name).lower()] for p in publication_datas}


def _subtype_xref_for_publication_data_list(publication_datas):
    logging.debug('_get_subtype_xref: started')

    descs = {p.subtype_description for p in publication_datas}

    q = select(Subtype.id, Subtype.description).where(Subtype.description.in_(descs))

    xref = {st['description'].lower(): st['id'] for st in db.session.execute(q).mappings()}

    new_subtypes = [Subtype(code=d, description=d) for d in descs if d.lower() not in xref.keys()]

    db.session.add_all(new_subtypes)
    db.session.commit()

    xref = xref | {st.description.lower(): st.id for st in new_subtypes}

    return {CatalogReference(p): xref[p.subtype_description.lower()] for p in publication_datas}


def _publication_xref_for_publication_data_list(publication_datas):
    logging.debug('_get_publication_xref: started')

    xref = {}

    keyfunc = lambda a: a.catalog

    for cat, pubs in groupby(sorted(publication_datas, key=keyfunc), key=keyfunc):
        q = select(CatalogPublication).where(
            CatalogPublication.catalog_identifier.in_([p.catalog_identifier for p in pubs])
        ).where(
            CatalogPublication.catalog == cat
        ).distinct()

        xref = xref | {CatalogReference(cp): cp.publication for cp in db.session.execute(q).unique().scalars()}

    new_pubs = {CatalogReference(p): Publication() for p in publication_datas if CatalogReference(p) not in xref.keys()}

    db.session.add_all(new_pubs.values())
    db.session.commit()

    xref = xref | new_pubs

    return {CatalogReference(p): xref[CatalogReference(p)] for p in publication_datas}


def _sponsor_xref_for_publication_data_list(publication_datas):
    logging.debug('_get_sponsor_xref: started')

    all_names = set(filter(None, [n for n in chain.from_iterable([p.funding_list for p in publication_datas])]))
    unique_names = {unidecode(n).lower(): n for n in all_names}

    q = select(Sponsor).where(Sponsor.name.in_(unique_names))

    xref = {unidecode(s.name).lower(): s for s in db.session.execute(q).scalars()}

    new_sponsors = [Sponsor(name=n) for u, n in unique_names.items() if u not in xref.keys()]

    db.session.add_all(new_sponsors)
    db.session.commit()

    xref = xref | {unidecode(s.name).lower(): s for s in new_sponsors}

    return {
        CatalogReference(p): [xref[unidecode(n).lower()] for n in p.funding_list if n]
        for p in publication_datas
    }


def _keyword_xref_for_publication_data_list(publication_datas):
    logging.debug('_get_keyword_xref: started')

    all_keywords = {k.strip() for k in chain.from_iterable([p.keywords for p in publication_datas]) if k}
    unique_keywords = {unidecode(k).lower(): k for k in all_keywords}

    q = select(Keyword).where(Keyword.keyword.in_(unique_keywords))

    print(unique_keywords)

    xref = {unidecode(k.keyword).lower(): k for k in db.session.execute(q).scalars()}

    print(xref)

    new_keywords = [Keyword(keyword=kw) for u, kw in unique_keywords.items() if u not in xref.keys()]

    print(new_keywords)

    db.session.add_all(new_keywords)
    db.session.commit()

    xref = xref | {unidecode(k.keyword).lower(): k for k in new_keywords}

    return {
        CatalogReference(p): [xref[unidecode(k.strip()).lower()] for k in p.keywords if k]
        for p in publication_datas
    }


def _affiliation_xref_for_author_data_list(author_datas):
    logging.debug('_get_affiliation_xref: started')

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

        new_affiliations = [
            Affiliation(
                catalog=cat,
                catalog_identifier=a.catalog_identifier,
                name=a.name,
                address=a.address,
                country=a.country,
                refresh_details=True,
            )
            for a in afils if CatalogReference(a) not in xref.keys()
        ]

        db.session.add_all(new_affiliations)
        db.session.commit()

        xref = xref | {CatalogReference(a): a for a in new_affiliations}

    results = {}

    for a in author_datas:
        results[CatalogReference(a)] = [xref[af] for af in {CatalogReference(af) for af in a.affiliations}]

    return results


def _source_xref_for_publication_data_list(publication_datas):
    logging.debug('_get_source_publication_xref: started')

    authors = {CatalogReference(a): a for a in chain.from_iterable([p.authors for p in publication_datas])}

    author_xref = _source_xref_for_author_data_list(authors.values())

    return {
        CatalogReference(p): [author_xref[CatalogReference(a)] for a in p.authors]
        for p in publication_datas
    }


def _source_xref_for_author_data_list(author_datas):
    logging.debug('_get_author_xref: started')

    xref = {}

    keyfunc = lambda a: a.catalog

    for cat, authors in groupby(sorted(author_datas, key=keyfunc), key=keyfunc):
        q = select(Source).where(
            Source.catalog_identifier.in_([a.catalog_identifier for a in authors])
        ).where(
            Source.catalog == cat
        )

        xref = xref | {CatalogReference(a): a for a in db.session.execute(q).scalars()}

    new_sources = [a.get_new_source() for a in author_datas if CatalogReference(a) not in xref.keys()]

    db.session.add_all(new_sources)
    db.session.commit()

    return xref | {CatalogReference(s): s for s in new_sources}
