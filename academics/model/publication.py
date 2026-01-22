from itertools import chain
import logging
from datetime import date
import re
from typing import Optional
from lbrc_flask.security import AuditMixin
from lbrc_flask.database import db
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Unicode, UnicodeText, UniqueConstraint, and_, func, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import SQLColumnExpression
from academics.model.catalog import CATALOG_MANUAL, CATALOG_OPEN_ALEX, CATALOG_SCOPUS
from academics.model.institutions import Institution
from sqlalchemy.ext.associationproxy import association_proxy


DOI_URL = 'doi.org'
ORCID_URL = 'orcid.org'


catalog_publications_sponsors = db.Table(
    'catalog_publications_sponsors',
    db.Column('sponsor_id', db.Integer(), db.ForeignKey('sponsor.id'), primary_key=True),
    db.Column('catalog_publication_id', db.Integer(), db.ForeignKey('catalog_publication.id'), primary_key=True),
)


catalog_publications_keywords = db.Table(
    'catalog_publication__keyword',
    db.Column('catalog_publication_id', db.Integer(), db.ForeignKey('catalog_publication.id'), primary_key=True),
    db.Column('keyword_id', db.Integer(), db.ForeignKey('keyword.id'), primary_key=True),
)

class FundingAcr(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))


class NihrAcknowledgement(db.Model):
    DEFAULT_VALUES = [
        {
            'name': 'NIHR Acknowledged',
            'acknowledged': True,
            'colour': '#F44336', # mid red
        },
        {
            'name': 'BRC Investigators Not A Primary Author',
            'acknowledged': False,
            'colour': '#3F51B5', # Mid blue
        },
        {
            'name': 'Need Senior Review',
            'acknowledged': False,
            'colour': '#009688', # teal
        },
        {
            'name': 'NIHR Not Acknowledged',
            'acknowledged': False,
            'colour': '#8BC34A', # light green
        },
        {
            'name': 'No BRC Investigator On Publication Or Not Relevant',
            'acknowledged': False,
            'colour': '#FF5722', # orangey red
        },
        {
            'name': 'Unable To Check - Full Paper Not Available',
            'acknowledged': False,
            'colour': '#9C27B0', # purple
        },
        {
            'name': 'Not to be Submitted',
            'acknowledged': False,
            'colour': '#47535E', # dark grey blue
        },
        {
            'name': 'Supplementary Material',
            'acknowledged': False,
            'colour': '#3f5921', # dark green
        },
    ]

    STRICT_STATEMENT_REGEX = [
        r'This (study|research) is funded by the National Institute for Health and Care Research \(NIHR\) Leicester Biomedical Research Centre. The views expressed are those of the author\(s\) and not necessarily those of the NIHR or the Department of Health and Social Care',
        r'This study has been delivered through the National Institute for Health and Care Research \(NIHR\) Leicester Biomedical Research Centre. The views expressed are those of the author\(s\) and not necessarily those of the .+, the NIHR or the Department of Health and Social Care',
        r'The research was carried out at the National Institute for Health and Care Research \(NIHR\) Leicester Biomedical Research Centre',
    ]

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))
    acknowledged = db.Column(db.Boolean)
    colour = db.Column(db.String(50))

    @classmethod
    def get_acknowledgement_by_name(cls, name):
        return db.session.execute(
            select(NihrAcknowledgement)
            .where(NihrAcknowledgement.name == name)
        ).scalar_one_or_none()

    @classmethod
    def get_acknowledged_status(cls):
        return cls.get_acknowledgement_by_name('NIHR Acknowledged')

    @classmethod
    def get_supplementary_status(cls):
        return cls.get_acknowledgement_by_name('Supplementary Material')

    @staticmethod
    def get_strict_match(text):
        for i, statement in enumerate(NihrAcknowledgement.STRICT_STATEMENT_REGEX, start=1):
            if re.search(statement, text):
                return i
        
        return None


class Subtype(db.Model):
    DEFAULT_VALUES = [
        {'code': 'article', 'description': 'article'},
        {'code': 'book', 'description': 'book'},
        {'code': 'correction', 'description': 'correction'},
    ]

    __table_args__ = (
        UniqueConstraint("description", name='ux__subtype__description'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(1000), nullable=True)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)

    @classmethod
    def get_validation_types(cls):
        return Subtype.query.filter(Subtype.description.in_(['article', 'book'])).all()


class Journal(db.Model):
    __table_args__ = (
        UniqueConstraint("name", name='ux__journal__name'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    preprint: Mapped[bool] = mapped_column(Boolean, nullable=True)


class Sponsor(db.Model):
    __table_args__ = (
        UniqueConstraint("name", name='ux__sponsor__name'),
    )

    NIHR_NAMES = [
        'NIHR',
        'National Institute for Health Research',
        'National Institute for Health and Care Research',
    ]

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[bool] = mapped_column(Boolean, nullable=True)

    catalog_publications = db.relationship("CatalogPublication", secondary=catalog_publications_sponsors, back_populates="sponsors", collection_class=set)

    @property
    def is_nihr(self):
        return any([n in self.name for n in self.NIHR_NAMES])


class Keyword(db.Model):
    __table_args__ = (
        UniqueConstraint("keyword", name='ux__keyword__keyword'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    keyword: Mapped[str] = mapped_column(String(1000), nullable=False)

    catalog_publications = db.relationship("CatalogPublication", secondary=catalog_publications_keywords, back_populates="keywords", collection_class=set)


institutions__publications = db.Table(
    'institutions__publications',
    db.Column('institution_id', db.Integer(), db.ForeignKey('institution.id'), primary_key=True),
    db.Column('publication_id', db.Integer(), db.ForeignKey('publication.id'), primary_key=True),
)

class Publication(db.Model, AuditMixin):
    id: Mapped[int] = mapped_column(primary_key=True)
    validation_historic: Mapped[bool] = mapped_column(default=False, nullable=True)
    not_brc: Mapped[bool] = mapped_column(default=False, nullable=True)
    doi: Mapped[str] = mapped_column(Unicode(1000), nullable=True, unique=True)
    vancouver: Mapped[str] = mapped_column(Unicode(1000), nullable=True)
    refresh_full_details: Mapped[bool] = mapped_column(Boolean, nullable=True)

    auto_nihr_acknowledgement_id = mapped_column(ForeignKey(NihrAcknowledgement.id), nullable=True)
    auto_nihr_acknowledgement: Mapped[NihrAcknowledgement] = relationship(
        lazy="selectin",
        foreign_keys=[auto_nihr_acknowledgement_id],
    )

    nihr_acknowledgement_id = mapped_column(ForeignKey(NihrAcknowledgement.id), nullable=True)
    nihr_acknowledgement: Mapped[NihrAcknowledgement] = relationship(
        lazy="selectin",
        foreign_keys=[nihr_acknowledgement_id],
    )

    strict_nihr_acknowledgement_match: Mapped[int] = mapped_column(nullable=True)

    preprint: Mapped[bool] = mapped_column(Boolean, nullable=True)

    institutions: Mapped[Institution] = relationship(
        "Institution",
        secondary=institutions__publications,
        collection_class=set,
    )

    folders = association_proxy('folder_dois', 'folder')

    @property
    def nihr_acknowledgement_name(self) -> str:
        if self.nihr_acknowledgement:
            return self.nihr_acknowledgement.name
        else:
            return ''

    @hybrid_property
    def is_industrial_collaboration(self):
        if self.institutions:
            return any([i.sector.lower() == 'corporate' for i in self.institutions])
        else:
            None

    @is_industrial_collaboration.inplace.expression
    @classmethod
    def _is_industrial_collaboration_expression(cls) -> SQLColumnExpression[Optional[Boolean]]:
        return (select(1)
             .where(institutions__publications.c.publication_id == cls.id)
             .where(Institution.id == institutions__publications.c.institution_id)
             .where(Institution.sector == 'corporate')).exists().label("is_industrial_collaboration")

    @hybrid_property
    def is_international_collaboration(self):
        if self.institutions:
            return any([i.country_code.lower() != 'gbr' for i in self.institutions])
        else:
            None

    @is_international_collaboration.inplace.expression
    @classmethod
    def _is_international_collaboration_expression(cls) -> SQLColumnExpression[Optional[Boolean]]:
        return (select(Institution.id)
            .where(institutions__publications.c.publication_id == cls.id)
            .where(Institution.id == institutions__publications.c.institution_id)
            .where(Institution.country_code != 'GBR')).exists().label("is_international_collaboration")

    @hybrid_property
    def is_external_collaboration(self):
        if self.institutions:
            return any([i.home_institution for i in self.institutions]) and any([not i.home_institution for i in self.institutions])
        else:
            None

    @is_external_collaboration.inplace.expression
    @classmethod
    def _is_external_collaboration_expression(cls) -> SQLColumnExpression[Optional[Boolean]]:
        return and_(
            (select(Institution.id)
            .where(institutions__publications.c.publication_id == cls.id)
            .where(Institution.id == institutions__publications.c.institution_id)
            .where(Institution.home_institution == 1)).exists(),
            (select(Institution.id)
            .where(institutions__publications.c.publication_id == cls.id)
            .where(Institution.id == institutions__publications.c.institution_id)
            .where(func.coalesce(Institution.home_institution, 0) == 0)).exists(),
            ).label("is_external_collaboration")

    @hybrid_property
    def is_theme_collaboration(self):
        return len(self.themes) > 1

    @property
    def scopus_catalog_publication(self):
        return next((cp for cp in self.catalog_publications if cp.catalog == CATALOG_SCOPUS), None)

    @property
    def openalex_catalog_publication(self):
        return next((cp for cp in self.catalog_publications if cp.catalog == CATALOG_OPEN_ALEX), None)

    @property
    def manual_catalog_publication(self):
        return next((cp for cp in self.catalog_publications if cp.catalog == CATALOG_MANUAL), None)

    @property
    def best_catalog_publication(self):
        return self.scopus_catalog_publication or self.openalex_catalog_publication or self.manual_catalog_publication or None

    @property
    def academics(self):
        return self.best_catalog_publication.academics

    @property
    def themes(self):
        return self.best_catalog_publication.themes
    
    def set_vancouver(self):
        if not self.best_catalog_publication:
            logging.warning(f'No best catalog publication for publication {self.id}')
            self.vancouver = '[No Best Catalog Publication]'
            return

        author_list = ', '.join([a.source.reference_name for a in self.best_catalog_publication.catalog_publication_sources[0:6]])

        if len(self.best_catalog_publication.catalog_publication_sources) > 6:
            author_list = f'{author_list}, et al'

        parts = []

        parts.append(author_list)
        parts.append(self.best_catalog_publication.title)
        
        if self.best_catalog_publication.journal:
            parts.append(self.best_catalog_publication.journal.name)
        
        pp = ''
        if self.best_catalog_publication.pages:
            pp = f'pp{self.best_catalog_publication.pages}'

        issue_volume = '/'.join(filter(None, [self.best_catalog_publication.issue, self.best_catalog_publication.volume]))

        parts.append(f'({self.best_catalog_publication.publication_cover_date:%B %y} {issue_volume} {pp})')

        self.vancouver = '. '.join(parts)

    @property
    def is_acknowledgement_unset(self):
        return self.auto_nihr_acknowledgement is None and self.nihr_acknowledgement is None

    @property
    def is_preprint_unset(self):
        return self.preprint is None

    def set_status_from_guess(self):
        if not self.is_acknowledgement_unset:
            return
        
        if self.is_nihr_acknowledged:
            self.nihr_acknowledgement = self.auto_nihr_acknowledgement = NihrAcknowledgement.get_acknowledged_status()
        if self.is_supplementary:
            self.nihr_acknowledgement = self.auto_nihr_acknowledgement = NihrAcknowledgement.get_supplementary_status()

    def set_strict_from_guess(self):
        self.strict_nihr_acknowledgement_match = NihrAcknowledgement.get_strict_match(self.best_catalog_publication.funding_text)

    def set_preprint_from_guess(self):
        if not self.is_preprint_unset:
            return
        
        if self.best_catalog_publication.journal:
            self.preprint = self.best_catalog_publication.journal.preprint

    @property
    def is_nihr_acknowledged(self):
        return any(chain(
            [s.is_nihr for s in self.best_catalog_publication.sponsors],
            [a.is_nihr for a in self.best_catalog_publication.affiliations]
        ))

    SUPPLEMENTARY_TITLE_ENDER = [
        r'abstract',
        r'errat',
        r'call for abstract',
        r'cheminform abstract',
        r'lsc abstract',
        r'late.breaking abstract',
        r'conference abstract',
        r'addend[^\s]*',
        r'table \d+',
        r'figure \d+',
        r'suppl[^\s]*',
    ]

    # Matches any type of bracket
    SUPPLEMENTARY_TEXT_PREPROCESS_REGEX = r"[\{\[\(\)\]\}]"

    @property
    def is_supplementary(self):
        if self._is_title_supplementary(self.best_catalog_publication.title):
            return True

        if self._is_issue_supplementary(self.best_catalog_publication.issue):
            return True

        if self._is_page_supplementary(self.best_catalog_publication.pages):
            return True

        return False
    
    def _is_title_supplementary(self, title):
        title = re.sub(self.SUPPLEMENTARY_TEXT_PREPROCESS_REGEX, '', title)

        if self._is_match_start_or_end(title, self.SUPPLEMENTARY_TITLE_ENDER):
            return True

        # Does title start with a code of the format 'X999' with any number of numbers?
        if re.search(r'^[A-Z]\d+', title, re.IGNORECASE):
            return True
        
        return False

    def _is_issue_supplementary(self, issue):
        issue = re.sub(self.SUPPLEMENTARY_TEXT_PREPROCESS_REGEX, '', issue)

        if re.search(r'suppl', issue, re.IGNORECASE):
            return True

        return False
    
    def _is_page_supplementary(self, page):
        # Does page title start with one of these letter?
        if re.search(r'^[ic]', page, re.IGNORECASE):
            return True

        return False
    
    def _is_match_start_or_end(self, text, regexes):
        for r in regexes:
            # text starts or ends with the pattern
            if re.search(f"^{r}|{r}$", text, re.IGNORECASE):
                return True

        return False


class CatalogPublication(db.Model, AuditMixin):
    __table_args__ = (
        UniqueConstraint("catalog", "catalog_identifier", name='ux__CatalogPublication__catalog__catalog_identifier'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    publication_id: Mapped[int] = mapped_column(ForeignKey(Publication.id))
    publication: Mapped[Publication] = relationship(
        backref=backref(
            "catalog_publications",
            cascade="delete, delete-orphan",
        )
    )
    refresh_full_details: Mapped[bool] = mapped_column(Boolean, nullable=True)
    catalog: Mapped[str] = mapped_column(String(50), index=True)
    catalog_identifier: Mapped[str] = mapped_column(String(500), index=True)

    doi: Mapped[str] = mapped_column(String(1000), index=True)
    title: Mapped[str] = mapped_column(Unicode(1000))
    publication_cover_date: Mapped[date]

    pubmed_id: Mapped[str] = mapped_column(String(50), index=True, nullable=True)
    abstract: Mapped[str] = mapped_column(UnicodeText)
    volume: Mapped[str] = mapped_column(String(100))
    issue: Mapped[str] = mapped_column(String(100))
    pages: Mapped[str] = mapped_column(String(100))
    funding_text: Mapped[str] = mapped_column(UnicodeText)
    is_open_access: Mapped[bool] = mapped_column(Boolean, nullable=True)
    cited_by_count: Mapped[int] = mapped_column(UnicodeText, nullable=True)
    href: Mapped[str] = mapped_column(UnicodeText)

    publication_year: Mapped[int] = mapped_column(Integer, nullable=True)
    publication_month: Mapped[int] = mapped_column(Integer, nullable=True)
    publication_day: Mapped[int] = mapped_column(Integer, nullable=True)
    publication_date_text: Mapped[str] = mapped_column(String(100), nullable=True)
    publication_period_start: Mapped[date] = mapped_column(Date, nullable=True)
    publication_period_end: Mapped[date] = mapped_column(Date, nullable=True)

    journal_id = mapped_column(ForeignKey(Journal.id), nullable=True)
    journal: Mapped[Journal] = relationship(lazy="selectin")

    subtype_id = mapped_column(ForeignKey(Subtype.id), nullable=True)
    subtype: Mapped[Subtype] = relationship(lazy="selectin")

    sponsors = db.relationship("Sponsor", lazy="selectin", secondary=catalog_publications_sponsors, back_populates="catalog_publications", collection_class=set)
    keywords = db.relationship("Keyword", lazy="selectin", secondary=catalog_publications_keywords, back_populates="catalog_publications", collection_class=set)

    @property
    def all_academics_left_brc(self):
        return all(cps.source.academic.has_left_brc for cps in self.brc_authors) and len(list(self.brc_authors)) > 0

    @property
    def brc_authors(self):
        return filter(lambda cps: cps.source.is_academic, self.catalog_publication_sources)

    @property
    def academics(self):
        return filter(None, (cps.source.academic for cps in self.catalog_publication_sources))

    @property
    def themes(self):
        return set(chain.from_iterable([a.themes for a in self.academics]))

    @property
    def author_count(self):
        return len(self.catalog_publication_sources)

    @property
    def affiliations(self):
        return set(chain.from_iterable([cps.source.affiliations for cps in self.catalog_publication_sources]))

    @property
    def author_list(self):
        return ', '.join([s.source.full_name for s in self.catalog_publication_sources])
