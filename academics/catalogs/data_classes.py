from dataclasses import dataclass
from academics.model import Keyword, Sponsor
from lbrc_flask.database import db
from academics.model import Source
from datetime import date


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