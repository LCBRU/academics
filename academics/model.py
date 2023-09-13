from lbrc_flask.security import AuditMixin
from lbrc_flask.model import CommonMixin
from lbrc_flask.database import db
from lbrc_flask.security import User as BaseUser
from itertools import chain

from sqlalchemy import func, select


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


class Academic(AuditMixin, CommonMixin, db.Model):
    # MariaDB backends need a VARChar variable, added 255 to set a max length

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    orcid = db.Column(db.String(255))
    updating = db.Column(db.Boolean, default=False)
    initialised = db.Column(db.Boolean, default=False)
    error = db.Column(db.Boolean, default=False)
    theme_id = db.Column(db.Integer, db.ForeignKey(Theme.id))
    theme = db.relationship(Theme)

    @property
    def full_name(self):
        return ' '.join(
            filter(len, [
                self.first_name,
                self.last_name,
            ])
        )

    def set_name(self):
        if not self.sources:
            return

        top_author = sorted(self.sources, key=lambda a: a.document_count, reverse=True)[0]

        self.first_name = top_author.first_name
        self.last_name = top_author.last_name

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
            self._best_source = sorted(self.sources, key=lambda x: x.document_count)[0]
            return self._best_source

    @property
    def publication_count(self):
        q =  (
            select(func.count(ScopusPublication.id))
            .where(ScopusPublication.sources.any(Source.academic_id == self.id))
        )

        return db.session.execute(q).scalar()

    
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

    source_id = db.Column(db.String(1000))
    orcid = db.Column(db.String(255))

    citation_count = db.Column(db.String(1000))
    document_count = db.Column(db.String(1000))
    h_index = db.Column(db.String(100))

    last_fetched_datetime = db.Column(db.DateTime)
    error = db.Column(db.Boolean, default=False)


class ScopusAuthor(Source):
    __tablename__ = "scopus_author"

    __mapper_args__ = {
        "polymorphic_load": "inline",
        "polymorphic_identity": "scopus",
    }

    id: db.Mapped[int] = db.mapped_column(db.ForeignKey("source.id"), primary_key=True)
    eid = db.Column(db.String(1000))
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    affiliation_id = db.Column(db.String(255))
    affiliation_name = db.Column(db.String(1000))
    affiliation_address = db.Column(db.String(1000))
    affiliation_city = db.Column(db.String(1000))
    affiliation_country = db.Column(db.String(1000))
    href = db.Column(db.String(1000))

    @property
    def full_name(self):
        return ' '.join(
            filter(len, [
                self.first_name,
                self.last_name,
            ])
        )

    @property
    def orcid_link(self):
        if self.orcid:
            return f'https://orcid.org/{self.orcid}'

    @property
    def affiliation_full_address(self):
        return ', '.join(
            filter(len, [
                self.affiliation_name,
                self.affiliation_address,
                self.affiliation_city,
                self.affiliation_country,
            ])
        )

    @property
    def orcid_mismatch(self):
        if self.academic.orcid and self.orcid:
            return self.academic.orcid != self.orcid
        else:
            return False


class Journal(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    # MariaDB backends need a VARChar variable, added 255 to set a max length
    name = db.Column(db.String(255))


scopus_author__scopus_publication = db.Table(
    'scopus_author__scopus_publication',
    db.Column('scopus_author_id', db.Integer(), db.ForeignKey('source.id'), primary_key=True),
    db.Column('scopus_publication_id', db.Integer(), db.ForeignKey('scopus_publication.id'), primary_key=True),
)


scopus_publications__keywords = db.Table(
    'scopus_publication__keyword',
    db.Column('scopus_publication_id', db.Integer(), db.ForeignKey('scopus_publication.id'), primary_key=True),
    db.Column('keyword_id', db.Integer(), db.ForeignKey('keyword.id'), primary_key=True),
)


folders__scopus_publications = db.Table(
    'folders__scopus_publications',
    db.Column('folder_id', db.Integer(), db.ForeignKey('folder.id'), primary_key=True),
    db.Column('scopus_publication_id', db.Integer(), db.ForeignKey('scopus_publication.id'), primary_key=True),
)


sponsors__scopus_publications = db.Table(
    'sponsors__scopus_publications',
    db.Column('sponsor_id', db.Integer(), db.ForeignKey('sponsor.id'), primary_key=True),
    db.Column('scopus_publication_id', db.Integer(), db.ForeignKey('scopus_publication.id'), primary_key=True),
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

    publications = db.relationship("ScopusPublication", secondary=sponsors__scopus_publications, back_populates="sponsors", collection_class=set)

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


class ScopusPublication(AuditMixin, CommonMixin, db.Model):

    ACKNOWLEDGEMENT_UNKNOWN = 'unknown'
    ACKNOWLEDGEMENT_ACKNOWLEDGED = 'acknowledged'
    ACKNOWLEDGEMENT_NOT_ACKNOWLEDGED = 'not_acknowledged'

    ACKNOWLEDGEMENTS = {
        ACKNOWLEDGEMENT_UNKNOWN: None,
        ACKNOWLEDGEMENT_ACKNOWLEDGED: True,
        ACKNOWLEDGEMENT_NOT_ACKNOWLEDGED: False,
    }

    OPEN_ACCESS_UNKNOWN = 'unknown'
    OPEN_ACCESS_OPEN_ACCESS = 'open_access'
    OPEN_ACCESS_NOT_OPEN_ACCESS = 'not_open_access'

    OPEN_ACCESS = {
        OPEN_ACCESS_UNKNOWN: None,
        OPEN_ACCESS_OPEN_ACCESS: True,
        OPEN_ACCESS_NOT_OPEN_ACCESS: False,
    }

    id = db.Column(db.Integer, primary_key=True)

    sources = db.relationship("Source", secondary=scopus_author__scopus_publication, backref=db.backref("scopus_publications"), lazy="joined")

    scopus_id = db.Column(db.String(1000))
    doi = db.Column(db.String(1000))
    title = db.Column(db.String(1000))
    publication_cover_date = db.Column(db.Date)
    pubmed_id = db.Column(db.String(1000))
    pii = db.Column(db.String(1000))
    abstract = db.Column(db.String(1000))
    author_list = db.Column(db.String(1000))
    volume = db.Column(db.String(1000))
    issue = db.Column(db.String(1000))
    pages = db.Column(db.String(1000))
    funding_text = db.Column(db.String(1000))
    is_open_access = db.Column(db.Boolean)
    cited_by_count = db.Column(db.Integer)

    href = db.Column(db.String(1000))
    deleted = db.Column(db.Boolean, default=False)

    validation_historic = db.Column(db.Boolean, default=None)

    auto_nihr_acknowledgement_id = db.Column(db.Integer, db.ForeignKey(NihrAcknowledgement.id))
    auto_nihr_acknowledgement = db.relationship(NihrAcknowledgement, foreign_keys=[auto_nihr_acknowledgement_id])

    auto_nihr_funded_open_access_id = db.Column(db.Integer, db.ForeignKey(NihrFundedOpenAccess.id))
    auto_nihr_funded_open_access = db.relationship(NihrFundedOpenAccess, foreign_keys=[auto_nihr_funded_open_access_id])

    nihr_acknowledgement_id = db.Column(db.Integer, db.ForeignKey(NihrAcknowledgement.id))
    nihr_acknowledgement = db.relationship(NihrAcknowledgement, foreign_keys=[nihr_acknowledgement_id], lazy="joined")

    nihr_funded_open_access_id = db.Column(db.Integer, db.ForeignKey(NihrFundedOpenAccess.id))
    nihr_funded_open_access = db.relationship(NihrFundedOpenAccess, foreign_keys=[nihr_funded_open_access_id], lazy="joined")

    journal_id = db.Column(db.Integer, db.ForeignKey(Journal.id))
    journal = db.relationship(Journal, lazy="joined", backref=db.backref("publications", cascade="all,delete"))

    subtype_id = db.Column(db.Integer, db.ForeignKey(Subtype.id))
    subtype = db.relationship(Subtype, lazy="joined", backref=db.backref("publications", cascade="all,delete"))

    keywords = db.relationship("Keyword", lazy="joined", secondary=scopus_publications__keywords, back_populates="publications", collection_class=set)
    folders = db.relationship("Folder", lazy="joined", secondary=folders__scopus_publications, back_populates="publications", collection_class=set)
    sponsors = db.relationship("Sponsor", lazy="joined", secondary=sponsors__scopus_publications, back_populates="publications", collection_class=set)

    @property
    def nihr_acknowledgement_yesno(self):
        if self.nihr_acknowledgement is None:
            return ''
        elif self.nihr_acknowledgement.acknowledged:
            return 'Yes'
        else:
            return 'No'
    
    @property
    def nihr_acknowledgement_detail(self):
        if self.nihr_acknowledgement is None or self.nihr_acknowledgement.acknowledged:
            return ''
        else:
            return self.nihr_acknowledgement.name
    
    @property
    def is_open_access_yesno(self):
        if self.is_open_access:
            return 'Yes'
        else:
            return 'No'
    
    @property
    def issue_volume(self):
        if self.issue and self.volume:
            return f' {self.issue}/{self.volume}'
        else:
            return ''

    @property
    def pp(self):
        if self.pages:
            return f' pp{self.pages}'
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
    def theme(self):
        themes = [a.theme.name for a in self.academics]
        return max(themes, key=themes.count)

    @property
    def is_nihr_acknowledged(self):
        return any([s.is_nihr for s in self.sponsors])

    @property
    def all_nihr_acknowledged(self):
        return len(self.sponsors) > 0 and all([s.is_nihr for s in self.sponsors])


class Keyword(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(1000))

    publications = db.relationship("ScopusPublication", secondary=scopus_publications__keywords, back_populates="keywords", collection_class=set)


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

    publications = db.relationship("ScopusPublication", secondary=folders__scopus_publications, back_populates="folders", collection_class=set)
    shared_users = db.relationship(User, secondary=folders__shared_users, backref=db.backref("shared_folders"), collection_class=set)

    @property
    def publication_count(self):
        return ScopusPublication.query.filter(ScopusPublication.folders.any(Folder.id == self.id)).count()


class Objective(db.Model, AuditMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))
    completed = db.Column(db.Boolean, default=False)

    theme_id = db.Column(db.Integer, db.ForeignKey(Theme.id))
    theme = db.relationship(Theme, backref=db.backref("objectives", cascade="all,delete"))


class Evidence(db.Model, AuditMixin):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.UnicodeText)

    objective_id = db.Column(db.Integer, db.ForeignKey(Objective.id))
    objective = db.relationship(Objective, backref=db.backref("evidences", cascade="all,delete"))

    __mapper_args__ = {
        "polymorphic_identity": "evidence",
        "polymorphic_on": "type",
    }


class EvidencePublication(Evidence):
    publication_id = db.Column(db.Integer, db.ForeignKey(ScopusPublication.id))
    publication = db.relationship(ScopusPublication, backref=db.backref("evidences", cascade="all,delete"))

    __mapper_args__ = {
        "polymorphic_identity": "publication",
    } 
