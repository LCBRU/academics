from lbrc_flask.security import AuditMixin
from lbrc_flask.model import CommonMixin
from lbrc_flask.database import db


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


class ScopusPublication(AuditMixin, CommonMixin, db.Model):

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

    href = db.Column(db.String)
    deleted = db.Column(db.Boolean, default=False)

    acknowledgement_validated = db.Column(db.Boolean, default=None)

    journal_id = db.Column(db.Integer, db.ForeignKey(Journal.id))
    journal = db.relationship(Journal, backref=db.backref("publications", cascade="all,delete"))

    keywords = db.relationship("Keyword", lazy="joined", secondary=scopus_publications__keywords, back_populates="publications", collection_class=set)


class Keyword(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String)

    publications = db.relationship("ScopusPublication", secondary=scopus_publications__keywords, back_populates="keywords", collection_class=set)
