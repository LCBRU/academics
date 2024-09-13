import re
from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, distinct, func, or_, select
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
from sqlalchemy.ext.orderinglist import ordering_list
from lbrc_flask.security import AuditMixin
from lbrc_flask.model import CommonMixin
from lbrc_flask.database import db
from academics.model.catalog import CATALOG_OPEN_ALEX, CATALOG_SCOPUS
from academics.model.publication import CatalogPublication, Publication
from academics.model.theme import Theme


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


academics_themes = db.Table(
    'academics_themes',
    db.Column(
        'academic_id',
        db.Integer(),
        db.ForeignKey('academic.id'),
        primary_key=True,
    ),
    db.Column(
        'theme_id',
        db.Integer(),
        db.ForeignKey('theme.id'),
        primary_key=True,
    ),
)


supplementary_authors = db.Table(
    'supplementary_authors',
    db.Column(
        'publication_id',
        db.Integer(),
        db.ForeignKey('publication.id'),
        primary_key=True,
    ),
    db.Column(
        'academic_id',
        db.Integer(),
        db.ForeignKey('academic.id'),
        primary_key=True,
    ),
)


class Affiliation(db.Model):
    __table_args__ = (
        UniqueConstraint("catalog", "catalog_identifier", name='ux__affiliation__catalog__catalog_identifier'),
    )

    id = db.Column(db.Integer, primary_key=True)
    catalog = db.Column(db.String(100), index=True)
    catalog_identifier = db.Column(db.String(1000), index=True)
    name = db.Column(db.String(1000))
    address = db.Column(db.String(1000))
    country = db.Column(db.String(100))
    refresh_details: Mapped[bool] = mapped_column(Boolean, nullable=True)
    home_organisation: Mapped[bool] = mapped_column(Boolean, nullable=True)
    international: Mapped[bool] = mapped_column(Boolean, nullable=True)
    industry: Mapped[bool] = mapped_column(Boolean, nullable=True)

    @property
    def line_summary(self):
        return ', '.join(filter(None, [self.name, self.address, self.country]))

    @property
    def summary(self):
        return '\n'.join(filter(None, [self.name, self.address, self.country]))

    NIHR_NAMES = [
        'NIHR',
        'National Institute for Health Research',
        'National Institute for Health and Care Research',
    ]

    @property
    def is_nihr(self):
        return any([n in self.name or '' for n in self.NIHR_NAMES])


class Academic(AuditMixin, CommonMixin, db.Model):
    # MariaDB backends need a VARChar variable, added 255 to set a max length

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(255), default='')
    last_name = db.Column(db.String(255), default='')
    initials = db.Column(db.String(255), default='')
    orcid = db.Column(db.String(255))
    google_scholar_id = db.Column(db.String(255))
    updating = db.Column(db.Boolean, default=False)
    initialised = db.Column(db.Boolean, default=False)
    error = db.Column(db.Boolean, default=False)
    has_left_brc = db.Column(db.Boolean, default=False, nullable=False)
    left_brc_date = db.Column(db.Date, nullable=True)

    themes = db.relationship(Theme, secondary='academics_themes', lazy="selectin")

    supplementary_publications = db.relationship(
        Publication,
        secondary=supplementary_authors,
        backref=backref("supplementary_authors"),
    )

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
            self.initials = self.best_source.initials or ''
        elif self.best_source.display_name:
            parts = self.best_source.display_name.strip().rsplit(maxsplit=1)
            self.first_name = parts[0] or ''
            self.last_name = parts[-1] or ''
            self.initials = ''

    @property
    def orcid_link(self):
        if self.orcid:
            return f'https://orcid.org/{self.orcid}'
        else:
            return "https://orcid.org/register"
        
    @property
    def google_scholar_link(self):
        if self.google_scholar_id:
            return f'https://scholar.google.com/citations?user={self.google_scholar_id}'
        else:
            return "https://scholar.google.com/intl/en/scholar/citations.html"
        
    @property
    def pubmed_link(self):
        if self.orcid:
            return f'https://pubmed.ncbi.nlm.nih.gov/?term=orcid {self.orcid}[auid]'
        else:
            regex = re.compile('[^a-zA-Z ]')
            name = ' '.join(filter(None, [
                regex.sub('', self.last_name or ''),
                regex.sub('', self.initials or ''),
            ]))

            return f"https://pubmed.ncbi.nlm.nih.gov/?term={name}[au]"
             
        
    @property
    def best_source(self):
        if hasattr(self, "_best_source"):
            return self._best_source
        elif len(self.sources) == 0:
            return None
        else:
            self._best_source = list(reversed(sorted(self.sources, key=lambda x: int(x.h_index or '0'))))[0]
            return self._best_source

    @property
    def sources_by_h_index(self):
        return list(reversed(sorted(self.sources, key=lambda x: int(x.h_index or '0'))))


    @property
    def publication_count(self) -> int:
        normal_ids = (
            select(distinct(Publication.id))
            .join(Publication.catalog_publications)
            .join(CatalogPublication.catalog_publication_sources)
            .join(CatalogPublicationsSources.source)
            .where(Source.academic_id == self.id)
        )

        supplementary_ids = (
            select(distinct(Publication.id))
            .join(Publication.supplementary_authors)
            .where(Academic.id == self.id)
        )

        q =  (
            select(func.count(distinct(Publication.id)))
            .where(or_(
                Publication.id.in_(normal_ids),
                Publication.id.in_(supplementary_ids),
            ))
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
        q =  (
            select(func.count(distinct(Academic.id)))
            .join(Academic.potential_sources)
            .join(AcademicPotentialSource.source)
            .where(AcademicPotentialSource.not_match == False)
            .where(Source.academic == None)
            .where(Academic.id == self.id)
        )

        return db.session.execute(q).scalar() > 0

    @property
    def theme_summary(self):
        return ', '.join([t.name for t in self.themes])

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
    academic = db.relationship(Academic, backref=db.backref("sources"))

    affiliations = db.relationship(
        Affiliation,
        secondary='sources__affiliations',
        cascade="all, delete",
        backref=db.backref("sources"),
    )

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
        elif self.catalog == CATALOG_OPEN_ALEX:
            return f'https://openalex.org/authors/{self.catalog_identifier}'

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
    
    @property
    def left_brc_date(self):
        if self.academic:
            return self.academic.left_brc_date
        else:
            return None
    
    @property
    def affiliation_summary(self):
        return '; '.join([a.name for a in self.affiliations])


class AcademicPotentialSource(AuditMixin, CommonMixin, db.Model):
    __table_args__ = (
        UniqueConstraint("academic_id", "source_id", name='ux__AcademicPotentialSource__academic_id__source_id'),
    )

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


    @property
    def can_unassign(self):
        return self.status in ['No Match', 'Match']

    @property
    def can_no_match(self):
        return self.status in ['Unassigned', 'Match']

    @property
    def can_match(self):
        return self.status in ['No Match', 'Unassigned']


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
    __table_args__ = (
        UniqueConstraint("catalog_publication_id", "ordinal", name='ux__CatalogPublicationsSources__cat_pub_id__ordinal'),
    )

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
    source: Mapped[Source] = relationship(
        backref=backref(
            'catalog_publication_sources',
            cascade="all, delete, delete-orphan",
        )
    )
    affiliations = db.relationship(
        Affiliation,
        secondary=catalog_publications_sources_affiliations,
        backref=backref("catalog_publication_sources"),
    )
