from lbrc_flask.security import AuditMixin
from lbrc_flask.model import CommonMixin
from lbrc_flask.database import db
from lbrc_flask.security import User


class Theme(AuditMixin, CommonMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)


class Academic(AuditMixin, CommonMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String)
    last_name = db.Column(db.String)
    updating = db.Column(db.Boolean, default=False)
    initialised = db.Column(db.Boolean, default=False)
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
        if not self.scopus_authors:
            return

        top_author = sorted(self.scopus_authors, key=lambda a: a.document_count, reverse=True)[0]

        self.first_name = top_author.first_name
        self.last_name = top_author.last_name


class ScopusAuthor(AuditMixin, CommonMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)
    academic_id = db.Column(db.Integer, db.ForeignKey(Academic.id))
    academic = db.relationship(Academic, backref=db.backref("scopus_authors", cascade="all,delete"))

    scopus_id = db.Column(db.String)
    eid = db.Column(db.String)
    first_name = db.Column(db.String)
    last_name = db.Column(db.String)
    affiliation_id = db.Column(db.String)
    affiliation_name = db.Column(db.String)
    affiliation_address = db.Column(db.String)
    affiliation_city = db.Column(db.String)
    affiliation_country = db.Column(db.String)
    citation_count = db.Column(db.String)
    document_count = db.Column(db.String)
    h_index = db.Column(db.String)
    href = db.Column(db.String)
    orcid = db.Column(db.String)

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


class Journal(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)


scopus_author__scopus_publication = db.Table(
    'scopus_author__scopus_publication',
    db.Column('scopus_author_id', db.Integer(), db.ForeignKey('scopus_author.id'), primary_key=True),
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
    code = db.Column(db.String)
    description = db.Column(db.String)

    @classmethod
    def get_validation_types(cls):
        return Subtype.query.filter(Subtype.description.in_(['article', 'book'])).all()


class Sponsor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

    publications = db.relationship("ScopusPublication", secondary=sponsors__scopus_publications, back_populates="sponsors", collection_class=set)


class FundingAcr(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)


class NihrFundedOpenAccess(db.Model):
    UKNOWN = 'unknown'
    NIHR_FUNDED = 'NIHR Funded'
    OTHER_NIHR_PROGRAMME_FUNDED = 'Other NIHR Programme Funded'
    OTHER_NIHR_INFRASTRUCTURE_FUNDED = 'Other NIHR Infrastructure Funded'
    NON_NIHR_FUNDED = 'Non NIHR Funded'

    all_details = [
        UKNOWN,
        NIHR_FUNDED,
        OTHER_NIHR_PROGRAMME_FUNDED,
        OTHER_NIHR_INFRASTRUCTURE_FUNDED,
        NON_NIHR_FUNDED,
    ]

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

    @classmethod
    def get_instance_by_name(cls, name):
        return NihrFundedOpenAccess.query.filter_by(name=name).one()


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

    scopus_authors = db.relationship("ScopusAuthor", secondary=scopus_author__scopus_publication, backref=db.backref("scopus_publications"), lazy="joined")

    scopus_id = db.Column(db.String)
    doi = db.Column(db.String)
    title = db.Column(db.String)
    publication_cover_date = db.Column(db.Date)
    pubmed_id = db.Column(db.String)
    pii = db.Column(db.String)
    abstract = db.Column(db.String)
    author_list = db.Column(db.String)
    volume = db.Column(db.String)
    issue = db.Column(db.String)
    pages = db.Column(db.String)
    funding_text = db.Column(db.String)
    is_open_access = db.Column(db.Boolean)
    cited_by_count = db.Column(db.Integer)

    href = db.Column(db.String)
    deleted = db.Column(db.Boolean, default=False)

    acknowledgement_validated = db.Column(db.Boolean, default=None)
    open_access_validated = db.Column(db.Boolean, default=None)
    validation_historic = db.Column(db.Boolean, default=None)

    journal_id = db.Column(db.Integer, db.ForeignKey(Journal.id))
    journal = db.relationship(Journal, lazy="joined", backref=db.backref("publications", cascade="all,delete"))

    subtype_id = db.Column(db.Integer, db.ForeignKey(Subtype.id))
    subtype = db.relationship(Subtype, lazy="joined", backref=db.backref("publications", cascade="all,delete"))

    keywords = db.relationship("Keyword", lazy="joined", secondary=scopus_publications__keywords, back_populates="publications", collection_class=set)
    folders = db.relationship("Folder", lazy="joined", secondary=folders__scopus_publications, back_populates="publications", collection_class=set)
    sponsors = db.relationship("Sponsor", lazy="joined", secondary=sponsors__scopus_publications, back_populates="publications", collection_class=set)

    @property
    def acknowledgement_status_name(self):
        if self.acknowledgement_validated is None:
            return 'Unknown'
        elif self.acknowledgement_validated:
            return 'Acknowledged'
        else:
            return 'Not Acknowledged'
    
    @property
    def open_access_status_name(self):
        if self.open_access_validated is None:
            return 'Unknown'
        elif self.open_access_validated:
            return 'Open Access'
        else:
            return 'Not Open Access'
    
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
    def folder_ids(self):
        return ','.join([str(f.id) for f in self.folders])


class Keyword(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String)

    publications = db.relationship("ScopusPublication", secondary=scopus_publications__keywords, back_populates="keywords", collection_class=set)


folders__shared_users = db.Table(
    'folders__shared_users',
    db.Column('folder_id', db.Integer(), db.ForeignKey('folder.id'), primary_key=True),
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id'), primary_key=True),
)


class Folder(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

    owner_id = db.Column(db.Integer, db.ForeignKey(User.id))
    owner = db.relationship(User, backref=db.backref("folders", cascade="all,delete"))

    publications = db.relationship("ScopusPublication", secondary=folders__scopus_publications, back_populates="folders", collection_class=set)
    shared_users = db.relationship("User", secondary=folders__shared_users, backref=db.backref("shared_folders"), collection_class=set)

    @property
    def publication_count(self):
        return ScopusPublication.query.filter(ScopusPublication.folders.any(Folder.id == self.id)).count()


def init_model(app):
    
    @app.before_first_request
    def data_setup():
        for name in NihrFundedOpenAccess.all_details:
            if NihrFundedOpenAccess.query.filter(NihrFundedOpenAccess.name == name).count() == 0:
                db.session.add(
                    NihrFundedOpenAccess(name=name)
                )

        db.session.commit()