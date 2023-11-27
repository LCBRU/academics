from datetime import date
from typing import List
from lbrc_flask.security import AuditMixin
from lbrc_flask.model import CommonMixin
from lbrc_flask.database import db
from lbrc_flask.security import User as BaseUser
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
from sqlalchemy import Boolean, ForeignKey, String, UnicodeText, func, select
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.ext.associationproxy import association_proxy, AssociationProxy


class Theme(AuditMixin, CommonMixin, db.Model):

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
    id = db.Column(db.Integer, primary_key=True)
    catalog = db.Column(db.String(100), index=True)
    catalog_identifier = db.Column(db.String(1000), index=True)
    name = db.Column(db.String(1000))
    address = db.Column(db.String(1000))
    country = db.Column(db.String(100))

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
            self.first_name = self.best_source.first_name
            self.last_name = self.best_source.last_name
        elif self.best_source.display_name:
            parts = self.best_source.display_name.strip().rsplit(maxsplit=1)
            self.first_name = parts[0]
            self.last_name = parts[-1]

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
            select(func.count(Publication.id))
            .where(Publication.publication_sources.any(PublicationsSources.source.academic_id == self.id))
        )

        print('^'*20)
        print(q)
        print('^'*20)

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
        return {s.source_identifier for s in self.sources if s.source_identifier and s.type == 'scopus'}


class Source(AuditMixin, CommonMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(100), nullable=False)

    __tablename__ = "source"
    __mapper_args__ = {
        "polymorphic_identity": "source",
        "polymorphic_on": "type",
    }

    academic_id = db.Column(db.Integer, db.ForeignKey(Academic.id))
    academic = db.relationship(Academic, backref=db.backref("sources", cascade="all,delete"))

    affiliation_id = db.Column(db.Integer, db.ForeignKey(Affiliation.id))
    affiliation = db.relationship(Affiliation, backref=db.backref("sources", cascade="all,delete"))

    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    initials = db.Column(db.String(255))
    display_name = db.Column(db.String(255))

    href = db.Column(db.String(1000))
    source_identifier = db.Column(db.String(1000))
    orcid = db.Column(db.String(255))

    citation_count = db.Column(db.String(1000))
    document_count = db.Column(db.String(1000))
    h_index = db.Column(db.String(100))

    last_fetched_datetime = db.Column(db.DateTime)
    error = db.Column(db.Boolean, default=False)

    @property
    def publication_count(self):
        q =  (
            select(func.count(Publication.id))
            .where(Publication.publication_sources.any(Source.id == self.id))
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


class ScopusAuthor(Source):
    __mapper_args__ = {
        "polymorphic_identity": "scopus",
    }


class OpenAlexAuthor(Source):
    __mapper_args__ = {
        "polymorphic_identity": "open alex",
    }


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


class Journal(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    # MariaDB backends need a VARChar variable, added 255 to set a max length
    name = db.Column(db.String(255))



publications__keywords = db.Table(
    'publication__keyword',
    db.Column('publication_id', db.Integer(), db.ForeignKey('publication.id'), primary_key=True),
    db.Column('keyword_id', db.Integer(), db.ForeignKey('keyword.id'), primary_key=True),
)


folders__publications = db.Table(
    'folders__publications',
    db.Column('folder_id', db.Integer(), db.ForeignKey('folder.id'), primary_key=True),
    db.Column('publication_id', db.Integer(), db.ForeignKey('publication.id'), primary_key=True),
)


sponsors__publications = db.Table(
    'sponsors__publications',
    db.Column('sponsor_id', db.Integer(), db.ForeignKey('sponsor.id'), primary_key=True),
    db.Column('publication_id', db.Integer(), db.ForeignKey('publication.id'), primary_key=True),
)


sources__publicationses = db.Table(
    'sources__publicationses',
    db.Column('source_id', db.Integer(), db.ForeignKey('source.id'), primary_key=True),
    db.Column('publication_id', db.Integer(), db.ForeignKey('publication.id'), primary_key=True),
)


class Subtype(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(1000))
    description = db.Column(db.String(10000))

    @classmethod
    def get_validation_types(cls):
        return Subtype.query.filter(Subtype.description.in_(['article', 'book'])).all()


class Sponsor(db.Model):
    NIHR_NAMES = [
        'NIHR',
        'National Institute for Health Research',
        'National Institute for Health and Care Research',
    ]

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))

    publicationses = db.relationship("Publication", secondary=sponsors__publications, back_populates="sponsors", collection_class=set)

    @property
    def is_nihr(self):
        return any([n in self.name for n in self.NIHR_NAMES])


class FundingAcr(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))


class NihrFundedOpenAccess(db.Model):
    UKNOWN = 'unknown'
    NIHR_FUNDED = 'NIHR Funded'
    OTHER_NIHR_PROGRAMME_FUNDED = 'Other NIHR Programme Funded'
    OTHER_NIHR_INFRASTRUCTURE_FUNDED = 'Other NIHR Infrastructure Funded'
    NON_NIHR_FUNDED = 'Non NIHR Funded'

    all_details = [
        NIHR_FUNDED,
        OTHER_NIHR_PROGRAMME_FUNDED,
        OTHER_NIHR_INFRASTRUCTURE_FUNDED,
        NON_NIHR_FUNDED,
    ]

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))

    @classmethod
    def get_instance_by_name(cls, name):
        return NihrFundedOpenAccess.query.filter_by(name=name).one()


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


class Keyword(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(1000))

    publicationses = db.relationship("Publication", secondary=publications__keywords, back_populates="keywords", collection_class=set)


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

    auto_nihr_acknowledgement_id = mapped_column(ForeignKey(NihrAcknowledgement.id), nullable=True)
    auto_nihr_acknowledgement: Mapped[NihrAcknowledgement] = relationship(lazy="joined", foreign_keys=[auto_nihr_acknowledgement_id])

    auto_nihr_funded_open_access_id = mapped_column(ForeignKey(NihrFundedOpenAccess.id), nullable=True)
    auto_nihr_funded_open_access: Mapped[NihrFundedOpenAccess] = relationship(lazy="joined", foreign_keys=[auto_nihr_funded_open_access_id])

    nihr_acknowledgement_id = mapped_column(ForeignKey(NihrAcknowledgement.id), nullable=True)
    nihr_acknowledgement: Mapped[NihrAcknowledgement] = relationship(lazy="joined", foreign_keys=[nihr_acknowledgement_id])

    nihr_funded_open_access_id = mapped_column(ForeignKey(NihrFundedOpenAccess.id), nullable=True)
    nihr_funded_open_access: Mapped[NihrFundedOpenAccess] = relationship(lazy="joined", foreign_keys=[nihr_funded_open_access_id])

    sources = db.relationship("Source", secondary=sources__publicationses, backref=db.backref("publications"), lazy="joined")
    publication_sources = db.relationship(
        "PublicationsSources",
        order_by="PublicationsSources.ordinal",
        collection_class=ordering_list('ordinal'),
        cascade="delete, delete-orphan"
    )

    authors: AssociationProxy[List[Source]] = association_proxy("publication_sources", "source")

    keywords = db.relationship("Keyword", lazy="joined", secondary=publications__keywords, back_populates="publicationses", collection_class=set)
    folders = db.relationship("Folder", lazy="joined", secondary=folders__publications, back_populates="publicationses", collection_class=set)
    sponsors = db.relationship("Sponsor", lazy="joined", secondary=sponsors__publications, back_populates="publicationses", collection_class=set)

    @property
    def scopus_catalog_publication(self):
        return next((cp for cp in self.catalog_publications if cp.catalog == 'scopus'))

    @property
    def openalex_catalog_publication(self):
        return next((cp for cp in self.catalog_publications if cp.catalog == 'open_alex'))

    @property
    def best_catalog_publication(self):
        return self.scopus_catalog_publication or self.openalex_catalog_publication or None

    @property
    def catalog(self) -> str:
        return self.best_catalog_publication.catalog

    @property
    def catalog_id(self) -> str:
        return self.best_catalog_publication.catalog_id

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
    def author_list(self) -> str:
        return self.best_catalog_publication.author_list

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
    def issue_volume(self):
        return '/'.join(filter(None, [self.issue, self.volume]))

    @property
    def pp(self):
        if self.pages:
            return f'pp{self.pages}'
        else:
            return ''

    @property
    def vancouverish(self):
        authors = (self.author_list or '').split(',')

        author_list = ', '.join(authors[0:6])

        if len(authors) > 6:
            author_list = f'{author_list}, et al'

        parts = []

        parts.append(author_list)
        parts.append(self.title)
        
        if self.journal:
            parts.append(self.journal.name)
        
        parts.append(f'({self.publication_cover_date:%B %y}{self.issue_volume}{self.pp})')

        return '. '.join(parts)

    @property
    def folder_ids(self):
        return ','.join([str(f.id) for f in self.folders])

    @property
    def academics(self):
        return {a.academic for a in self.sources}

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
    publication: Mapped[Publication] = relationship(lazy="joined", backref=backref("catalog_publications", lazy="joined"))
    is_main: Mapped[bool] = mapped_column(Boolean, nullable=True)
    catalog: Mapped[str] = mapped_column(String(50), index=True)
    catalog_identifier: Mapped[str] = mapped_column(String(500), index=True)

    doi: Mapped[str] = mapped_column(String(1000), index=True)
    title: Mapped[str] = mapped_column(String(1000))
    publication_cover_date: Mapped[date]

    pubmed_id: Mapped[str] = mapped_column(String(50), index=True, nullable=True)
    abstract: Mapped[str] = mapped_column(UnicodeText)
    author_list: Mapped[str] = mapped_column(UnicodeText)
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


class PublicationsSources(db.Model):
    publication_id: Mapped[int] = mapped_column(ForeignKey(Publication.id), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey(Source.id), primary_key=True)
    ordinal: Mapped[int] = mapped_column(primary_key=True)

    publication: Mapped[Publication] = relationship()
    source: Mapped[Source] = relationship()
