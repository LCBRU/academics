from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, distinct, func, select
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
from sqlalchemy.ext.orderinglist import ordering_list
from lbrc_flask.security import AuditMixin
from lbrc_flask.model import CommonMixin
from lbrc_flask.database import db
from academics.model.catalog import CATALOG_SCOPUS
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

    themes = db.relationship(Theme, secondary='academics_themes', cascade="all,delete")

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
    source: Mapped[Source] = relationship()
    affiliations = db.relationship(
        Affiliation,
        secondary=catalog_publications_sources_affiliations,
    )
