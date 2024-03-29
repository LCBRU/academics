import logging
from datetime import date
from typing import Optional
from lbrc_flask.security import AuditMixin
from lbrc_flask.database import db
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
from sqlalchemy import Boolean, ForeignKey, String, Unicode, UnicodeText, UniqueConstraint, and_, func, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import SQLColumnExpression
from academics.model.catalog import CATALOG_OPEN_ALEX, CATALOG_SCOPUS
from academics.model.institutions import Institution


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
    def sponsors(self):
        return self.best_catalog_publication.sponsors

    @property
    def keywords(self):
        return self.best_catalog_publication.keywords

    @property
    def academics(self):
        return self.best_catalog_publication.academics

    @property
    def scopus_catalog_publication(self):
        return next((cp for cp in self.catalog_publications if cp.catalog == CATALOG_SCOPUS), None)

    @property
    def openalex_catalog_publication(self):
        return next((cp for cp in self.catalog_publications if cp.catalog == CATALOG_OPEN_ALEX), None)

    @property
    def best_catalog_publication(self):
        return self.scopus_catalog_publication or self.openalex_catalog_publication or None

    @property
    def catalog(self) -> str:
        return self.best_catalog_publication.catalog

    @property
    def catalog_identifier(self) -> str:
        return self.best_catalog_publication.catalog_identifier

    @property
    def title(self) -> str:
        return self.best_catalog_publication.title

    @property
    def publication_cover_date(self) -> date:
        return self.best_catalog_publication.publication_cover_date

    @property
    def pubmed_id(self) -> str:
        return self.best_catalog_publication.pubmed_id

    @property
    def pii(self) -> str:
        return self.best_catalog_publication.pii

    @property
    def abstract(self) -> str:
        return self.best_catalog_publication.abstract

    @property
    def volume(self) -> str:
        return self.best_catalog_publication.volume

    @property
    def issue(self) -> str:
        return self.best_catalog_publication.issue

    @property
    def pages(self) -> str:
        return self.best_catalog_publication.pages

    @property
    def funding_text(self) -> str:
        return self.best_catalog_publication.funding_text

    @property
    def is_open_access(self) -> bool:
        return self.best_catalog_publication.is_open_access

    @property
    def cited_by_count(self) -> int:
        return self.best_catalog_publication.cited_by_count

    @property
    def href(self) -> str:
        return self.best_catalog_publication.href

    @property
    def journal_id(self) -> int:
        return self.best_catalog_publication.journal_id

    @property
    def journal(self) -> Journal:
        return self.best_catalog_publication.journal

    @property
    def subtype_id(self) -> int:
        return self.best_catalog_publication.subtype_id

    @property
    def subtype(self) -> Subtype:
        return self.best_catalog_publication.subtype

    @property
    def authors(self) -> Subtype:
        return self.best_catalog_publication.authors

    @property
    def issue_volume(self):
        return '/'.join(filter(None, [self.issue, self.volume]))

    @property
    def pp(self):
        if self.pages:
            return f'pp{self.pages}'
        else:
            return ''

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
        parts.append(self.title)
        
        if self.journal:
            parts.append(self.journal.name)
        
        pp = ''
        if self.pages:
            pp = f'pp{self.pages}'

        issue_volume = '/'.join(filter(None, [self.issue, self.volume]))

        parts.append(f'({self.publication_cover_date:%B %y}{issue_volume}{pp})')

        self.vancouver = '. '.join(parts)

    @property
    def folder_ids(self):
        return ','.join([str(f.id) for f in self.folders])

    @property
    def is_nihr_acknowledged(self):
        return any([s.is_nihr for s in self.sponsors])

    @property
    def all_academics_left_brc(self):
        return self.best_catalog_publication.all_academics_left_brc


class CatalogPublication(db.Model, AuditMixin):
    __table_args__ = (
        UniqueConstraint("catalog", "catalog_identifier", name='ux__CatalogPublication__catalog__catalog_identifier'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    publication_id: Mapped[int] = mapped_column(ForeignKey(Publication.id))
    publication: Mapped[Publication] = relationship(
        backref=backref(
            "catalog_publications",
            lazy="joined",
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

    journal_id = mapped_column(ForeignKey(Journal.id))
    journal: Mapped[Journal] = relationship(lazy="selectin")

    subtype_id = mapped_column(ForeignKey(Subtype.id))
    subtype: Mapped[Subtype] = relationship(lazy="selectin")

    sponsors = db.relationship("Sponsor", lazy="selectin", secondary=catalog_publications_sponsors, back_populates="catalog_publications", collection_class=set)
    keywords = db.relationship("Keyword", lazy="selectin", secondary=catalog_publications_keywords, back_populates="catalog_publications", collection_class=set)

    @property
    def all_academics_left_brc(self):
        return all(cps.source.academic.has_left_brc for cps in self.catalog_publication_sources)

    @property
    def academics(self):
        return filter(None, (cps.source.academic for cps in self.catalog_publication_sources))

    @property
    def author_count(self):
        return len(self.catalog_publication_sources)
