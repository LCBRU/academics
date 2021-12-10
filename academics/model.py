from lbrc_flask.security import AuditMixin
from lbrc_flask.model import CommonMixin
from lbrc_flask.database import db


class Academic(AuditMixin, CommonMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String)
    last_name = db.Column(db.String)
    updating = db.Column(db.Boolean, default=False)
    initialised = db.Column(db.Boolean, default=False)

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

    @property
    def full_name(self):
        return ' '.join(
            filter(len, [
                self.first_name,
                self.last_name,
            ])
        )

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


scopus_author__scopus_publication = db.Table(
    'scopus_author__scopus_publication',
    db.Column('scopus_author_id', db.Integer(), db.ForeignKey('scopus_author.id'), primary_key=True),
    db.Column('scopus_publication_id', db.Integer(), db.ForeignKey('scopus_publication.id'), primary_key=True),
)


class ScopusPublication(AuditMixin, CommonMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)

    scopus_authors = db.relationship("ScopusAuthor", secondary=scopus_author__scopus_publication, backref=db.backref("scopus_publications", lazy="joined"), collection_class=set)

    scopus_id = db.Column(db.String)
    doi = db.Column(db.String)
    title = db.Column(db.String)
    publication = db.Column(db.String)
    publication_cover_date = db.Column(db.Date)

    href = db.Column(db.String)
    deleted = db.Column(db.Boolean, default=False)
