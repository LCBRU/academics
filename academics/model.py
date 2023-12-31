from datetime import date
import logging
from typing import List
from lbrc_flask.security import AuditMixin
from lbrc_flask.model import CommonMixin
from lbrc_flask.database import db
from lbrc_flask.security import User as BaseUser
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
from sqlalchemy import Boolean, ForeignKey, String, UnicodeText, UniqueConstraint, distinct, func, select
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.ext.associationproxy import association_proxy, AssociationProxy


CATALOG_SCOPUS = 'scopus'
CATALOG_OPEN_ALEX = 'open alex'

DOI_URL = 'doi.org'
ORCID_URL = 'orcid.org'


class Theme(AuditMixin, CommonMixin, db.Model):
    __table_args__ = (
        UniqueConstraint("name", name='ux__theme__name'),
    )

    id = db.Column(db.Integer, primary_key=True)
    # MariaDB backends need a VARChar variable, added 255 to set a max length
    name = db.Column(db.String(255))

    def __str__(self):
        return self.name or ""


class User(BaseUser):
    __table_args__ = {'extend_existing': True}

    theme_id = db.Column(db.Integer, db.ForeignKey(Theme.id))
    theme = db.relationship(Theme)


class Affiliation(db.Model):
    # __table_args__ = (
    #     UniqueConstraint("catalog", "catalog_identifier", name='ux__affiliation__catalog__catalog_identifier'),
    # )

    id = db.Column(db.Integer, primary_key=True)
    catalog = db.Column(db.String(100), index=True)
    catalog_identifier = db.Column(db.String(1000), index=True)
    name = db.Column(db.String(1000))
    address = db.Column(db.String(1000))
    country = db.Column(db.String(100))
    refresh_details: Mapped[bool] = mapped_column(Boolean, nullable=True)

    @property
    def line_summary(self):
        return ', '.join(filter(None, [self.name, self.address, self.country]))

    @property
    def summary(self):
        return '\n'.join(filter(None, [self.name, self.address, self.country]))


class Academic(AuditMixin, CommonMixin, db.Model):
    # MariaDB backends need a VARChar variable, added 255 to set a max length

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(255), default='')
    last_name = db.Column(db.String(255), default='')
    orcid = db.Column(db.String(255))
    updating = db.Column(db.Boolean, default=False)
    initialised = db.Column(db.Boolean, default=False)
    error = db.Column(db.Boolean, default=False)
    theme_id = db.Column(db.Integer, db.ForeignKey(Theme.id))
    theme = db.relationship(Theme)
    has_left_brc = db.Column(db.Boolean, default=False, nullable=False)

    @property
    def full_name(self):
        return ' '.join(
            filter(len, [
                self.first_name,
                self.last_name,
            ])
        )

    def ensure_initialisation(self):
        if self.best_source.last_name:
            self.first_name = self.best_source.first_name or ''
            self.last_name = self.best_source.last_name or ''
        elif self.best_source.display_name:
            parts = self.best_source.display_name.strip().rsplit(maxsplit=1)
            self.first_name = parts[0] or ''
            self.last_name = parts[-1] or ''

    @property
    def orcid_link(self):
        if self.orcid:
            return f'https://orcid.org/{self.orcid}'

    @property
    def best_source(self):
        if hasattr(self, "_best_source"):
            return self._best_source
        elif len(self.sources) == 0:
            return None
        else:
            self._best_source = sorted(self.sources, key=lambda x: x.document_count or '')[0]
            return self._best_source

    @property
    def publication_count(self):
        q =  (
            select(func.count(distinct(Publication.id)))
            .join(Publication.catalog_publications)
            .join(CatalogPublication.catalog_publication_sources)
            .join(CatalogPublicationsSources.source)
            .where(Source.academic_id == self.id)
        )

        return db.session.execute(q).scalar()    

    @property
    def orcid_mismatch(self):
        return any([s.orcid_mismatch for s in self.sources])

    @property
    def source_errors(self):
        return any([s.error for s in self.sources])

    @property
    def has_new_potential_sources(self):
        return any(p for p in self.potential_sources if not p.not_match and p.source.academic is None)

    def mark_for_update(self):
        for au in self.sources:
            au.error = False
        
        self.error = False
        self.updating = True        

    def all_orcids(self):
        return {self.orcid} | {s.orcid for s in self.sources if s.orcid}

    def all_scopus_ids(self):
        return {s.catalog_identifier for s in self.sources if s.catalog_identifier and s.catalog == 'scopus'}


class Source(AuditMixin, CommonMixin, db.Model):
    __table_args__ = (
        UniqueConstraint("catalog", "catalog_identifier", name='ux__source__catalog__catalog_identifier'),
    )

    id = db.Column(db.Integer, primary_key=True)
    catalog: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    catalog_identifier: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    academic_id = db.Column(db.Integer, db.ForeignKey(Academic.id))
    academic = db.relationship(Academic, backref=db.backref("sources", cascade="all,delete"))

    affiliations = db.relationship(Affiliation, secondary='sources__affiliations', cascade="all,delete")

    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    initials = db.Column(db.String(255))
    display_name = db.Column(db.String(255))

    href = db.Column(db.String(1000))
    orcid = db.Column(db.String(255))

    citation_count = db.Column(db.String(1000))
    document_count = db.Column(db.String(1000))
    h_index = db.Column(db.String(100))

    last_fetched_datetime = db.Column(db.DateTime)
    error = db.Column(db.Boolean, default=False)

    @property
    def author_url(self):
        if self.catalog == CATALOG_SCOPUS:
            return f'https://www.scopus.com/authid/detail.uri?authorId={self.catalog_identifier}'

    @property
    def publication_count(self):
        q =  (
            select(func.count(distinct(Publication.id)))
            .join(Publication.catalog_publications)
            .join(CatalogPublication.catalog_publication_sources)
            .where(CatalogPublicationsSources.source_id == self.id)
        )

        return db.session.execute(q).scalar()

    @property
    def orcid_mismatch(self):
        if self.academic.orcid and self.orcid:
            return self.academic.orcid != self.orcid
        else:
            return False

    @property
    def orcid_link(self):
        if self.orcid:
            return f'https://orcid.org/{self.orcid}'

    @property
    def full_name(self):
        if self.last_name:
            return ' '.join(filter(None, [self.first_name, self.initials, self.last_name]))
        else:
            return self.display_name

    @property
    def reference_name(self):
        if self.last_name:
            return ' '.join(filter(None, [self.last_name, self.initials]))
        else:
            return self.display_name

    @property
    def is_academic(self):
        return self.academic is not None

    @property
    def has_left_brc(self):
        if self.academic:
            return self.academic.has_left_brc
        else:
            return None


class AcademicPotentialSource(AuditMixin, CommonMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    academic_id = db.Column(db.Integer, db.ForeignKey(Academic.id), nullable=False)
    academic = db.relationship(Academic, backref=db.backref("potential_sources", cascade="all,delete"))
    source_id = db.Column(db.Integer, db.ForeignKey(Source.id), nullable=False)
    source = db.relationship(Source, backref=db.backref("potential_academics", cascade="all,delete"))
    not_match = db.Column(db.Boolean, default=False)

    @property
    def status(self):
        if self.not_match:
            return "No Match"
        elif self.source.academic is None:
            return "Unassigned"
        elif self.source.academic == self.academic:
            return "Match"
        else:
            return f"Assigned to {self.source.academic.full_name}"


folders__publications = db.Table(
    'folders__publications',
    db.Column('folder_id', db.Integer(), db.ForeignKey('folder.id'), primary_key=True),
    db.Column('publication_id', db.Integer(), db.ForeignKey('publication.id'), primary_key=True),
)


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


sources__affiliations = db.Table(
    'sources__affiliations',
    db.Column(
        'source_id',
        db.Integer(),
        db.ForeignKey('source.id'),
        primary_key=True,
    ),
    db.Column(
        'affiliation_id',
        db.Integer(),
        db.ForeignKey('affiliation.id'),
        primary_key=True,
    ),
)


class FundingAcr(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))


class NihrAcknowledgement(db.Model):
    UKNOWN = 'unknown'
    NIHR_ACKNOWLEDGED = 'NIHR Acknowledged'
    NIHR_NOT_ACKNOWLEDGED = 'NIHR Not Acknowledged'
    UNABLE_TO_CHECK = 'Unable to check - full paper not available'
    NIHR_NOT_ACKNOWLEDGED_NO_BRC_INVESTIGATORS = 'BRC Investigator associated with study and NIHR not Acknowledged'
    NIHR_NOT_ACKNOWLEDGED_WITH_BRC_INVESTIGATORS = 'No BRC Investigator associated with study and NIHR not Acknowledged'
    NIHR_NOT_ACKNOWLEDGED_BRC_INVESTIGATORS_NOT_PRIMARY = 'BRC Investigators not a primary author'

    all_details = {
        NIHR_ACKNOWLEDGED: True,
        NIHR_NOT_ACKNOWLEDGED: False,
        UNABLE_TO_CHECK: False,
        NIHR_NOT_ACKNOWLEDGED_NO_BRC_INVESTIGATORS: False,
        NIHR_NOT_ACKNOWLEDGED_WITH_BRC_INVESTIGATORS: False,
        NIHR_NOT_ACKNOWLEDGED_BRC_INVESTIGATORS_NOT_PRIMARY: False,
    }

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))
    acknowledged = db.Column(db.Boolean)

    @classmethod
    def get_instance_by_name(cls, name):
        return NihrAcknowledgement.query.filter_by(name=name).one()


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
    name: Mapped[str] = mapped_column(String(255), nullable=False)


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


folders__shared_users = db.Table(
    'folders__shared_users',
    db.Column('folder_id', db.Integer(), db.ForeignKey('folder.id'), primary_key=True),
    db.Column('user_id', db.Integer(), db.ForeignKey(User.id), primary_key=True),
)


class Folder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))

    owner_id = db.Column(db.Integer, db.ForeignKey(User.id))
    owner = db.relationship(User, backref=db.backref("folders", cascade="all,delete"))

    publicationses = db.relationship("Publication", secondary=folders__publications, back_populates="folders", collection_class=set)
    shared_users = db.relationship(User, secondary=folders__shared_users, backref=db.backref("shared_folders"), collection_class=set)

    @property
    def publication_count(self):
        return Publication.query.filter(Publication.folders.any(Folder.id == self.id)).count()


class Objective(db.Model, AuditMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))
    completed = db.Column(db.Boolean, default=False)

    theme_id = db.Column(db.Integer, db.ForeignKey(Theme.id))
    theme = db.relationship(Theme, backref=db.backref("objectives", cascade="all,delete"))


class Publication(db.Model, AuditMixin):
    id: Mapped[int] = mapped_column(primary_key=True)
    validation_historic: Mapped[bool] = mapped_column(default=False, nullable=True)
    not_brc: Mapped[bool] = mapped_column(default=False, nullable=True)
    vancouver: Mapped[str] = mapped_column(nullable=True)

    auto_nihr_acknowledgement_id = mapped_column(ForeignKey(NihrAcknowledgement.id), nullable=True)
    auto_nihr_acknowledgement: Mapped[NihrAcknowledgement] = relationship(lazy="joined", foreign_keys=[auto_nihr_acknowledgement_id])

    nihr_acknowledgement_id = mapped_column(ForeignKey(NihrAcknowledgement.id), nullable=True)
    nihr_acknowledgement: Mapped[NihrAcknowledgement] = relationship(lazy="joined", foreign_keys=[nihr_acknowledgement_id])

    folders = db.relationship("Folder", lazy="joined", secondary=folders__publications, back_populates="publicationses", collection_class=set)

    @property
    def sponsors(self):
        return self.best_catalog_publication.sponsors

    @property
    def keywords(self):
        return self.best_catalog_publication.keywords

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
    def doi(self) -> str:
        return self.best_catalog_publication.doi

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

        author_list = ', '.join([a.reference_name for a in self.authors[0:6]])

        if len(self.authors) > 6:
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
    def academics(self):
        return {a.academic for a in self.authors}

    @property
    def is_nihr_acknowledged(self):
        return any([s.is_nihr for s in self.sponsors])

    @property
    def all_nihr_acknowledged(self):
        return len(self.sponsors) > 0 and all([s.is_nihr for s in self.sponsors])

    @property
    def all_academics_left_brc(self):
        return all(a.has_left_brc for a in self.academics)


class CatalogPublication(db.Model, AuditMixin):
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
    title: Mapped[str] = mapped_column(String(1000))
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
    journal: Mapped[Journal] = relationship(lazy="joined")

    subtype_id = mapped_column(ForeignKey(Subtype.id))
    subtype: Mapped[Subtype] = relationship(lazy="joined")

    authors: AssociationProxy[List[Source]] = association_proxy("catalog_publication_sources", "source")
    sponsors = db.relationship("Sponsor", lazy="joined", secondary=catalog_publications_sponsors, back_populates="catalog_publications", collection_class=set)
    keywords = db.relationship("Keyword", lazy="joined", secondary=catalog_publications_keywords, back_populates="catalog_publications", collection_class=set)


catalog_publications_sources_affiliations = db.Table(
    'catalog_publications_sources__affiliations',
    db.Column(
        'catalog_publications_sources_id',
        db.Integer(),
        db.ForeignKey('catalog_publications_sources.id'),
        primary_key=True,
    ),
    db.Column(
        'affiliation_id',
        db.Integer(),
        db.ForeignKey('affiliation.id'),
        primary_key=True,
    ),
)


class CatalogPublicationsSources(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    catalog_publication_id: Mapped[int] = mapped_column(ForeignKey(CatalogPublication.id), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey(Source.id), index=True)
    ordinal: Mapped[int] = mapped_column()

    catalog_publication: Mapped[CatalogPublication] = relationship(
        backref=backref(
            "catalog_publication_sources",
            order_by="CatalogPublicationsSources.ordinal",
            collection_class=ordering_list('ordinal'),
            cascade="all, delete, delete-orphan",
        ),
    )
    source: Mapped[Source] = relationship()
    affiliations = db.relationship(
        Affiliation,
        secondary=catalog_publications_sources_affiliations,
    )
