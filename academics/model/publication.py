from itertools import chain
import logging
from datetime import date
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
from sqlalchemy.dialects.mysql import LONGTEXT


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
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))
    acknowledged = db.Column(db.Boolean)
    colour = db.Column(db.String(50))

    @classmethod
    def get_acknowledged_status(cls):
        return NihrAcknowledgement.query.filter_by(name='NIHR Acknowledged').one()


class Subtype(db.Model):
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
    auto_nihr_acknowledgement: Mapped[NihrAcknowledgement] = relationship(lazy="selectin", foreign_keys=[auto_nihr_acknowledgement_id])

    nihr_acknowledgement_id = mapped_column(ForeignKey(NihrAcknowledgement.id), nullable=True)
    nihr_acknowledgement: Mapped[NihrAcknowledgement] = relationship(lazy="selectin", foreign_keys=[nihr_acknowledgement_id])

    preprint: Mapped[bool] = mapped_column(Boolean, nullable=True)

    institutions: Mapped[Institution] = relationship(
        "Institution",
        secondary=institutions__publications,
        collection_class=set,
    )

    folders = association_proxy('folder_dois', 'folder')

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
            return any([i.home_organisation for i in self.institutions]) and any([not i.home_organisation for i in self.institutions])
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

    def set_vancouver(self):
        if not self.best_catalog_publication:
            logging.warn(f'No best catalog publication for publication {self.id}')
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

        parts.append(f'({self.best_catalog_publication.publication_cover_date:%B %y}{issue_volume}{pp})')

        self.vancouver = '. '.join(parts)

    @property
    def is_nihr_acknowledged(self):
        return any(chain(
            [s.is_nihr for s in self.best_catalog_publication.sponsors],
            [a.is_nihr for a in self.best_catalog_publication.affiliations]
        ))


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
    def author_count(self):
        return len(self.catalog_publication_sources)

    @property
    def affiliations(self):
        return set(chain.from_iterable([cps.source.affiliations for cps in self.catalog_publication_sources]))
