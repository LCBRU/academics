from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import backref
from lbrc_flask.database import db

from academics.model.publication import Publication
from academics.model.security import User


folders__shared_users = db.Table(
    'folders__shared_users',
    db.Column('folder_id', db.Integer(), db.ForeignKey('folder.id'), primary_key=True),
    db.Column('user_id', db.Integer(), db.ForeignKey(User.id), primary_key=True),
)


folders__publications = db.Table(
    'folders__publications',
    db.Column('folder_id', db.Integer(), db.ForeignKey('folder.id'), primary_key=True),
    db.Column('publication_id', db.Integer(), db.ForeignKey('publication.id'), primary_key=True),
)


class Folder(db.Model):
    __table_args__ = (
        UniqueConstraint("name", "owner_id", name='ux__folder__name__owner_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))

    owner_id = db.Column(db.Integer, db.ForeignKey(User.id))
    owner = db.relationship(User, backref=db.backref("folders", cascade="all,delete"))

    publicationses = db.relationship(
        "Publication",
        secondary=folders__publications,
        collection_class=set,
        backref=backref(
            "folders",
            collection_class=set,
        )
    )
    shared_users = db.relationship(User, secondary=folders__shared_users, backref=db.backref("shared_folders"), collection_class=set)

    @property
    def publication_count(self):
        return Publication.query.filter(Publication.folders.any(Folder.id == self.id)).count()


