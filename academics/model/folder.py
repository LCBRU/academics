from sqlalchemy import ForeignKey, Index, Unicode, UniqueConstraint
from sqlalchemy.orm import backref
from lbrc_flask.database import db
from lbrc_flask.validators import is_invalid_doi

from academics.model.publication import Publication
from academics.model.security import User
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref


folders__shared_users = db.Table(
    'folders__shared_users',
    db.Column('folder_id', db.Integer(), db.ForeignKey('folder.id'), primary_key=True),
    db.Column('user_id', db.Integer(), db.ForeignKey(User.id), primary_key=True),
)


class Folder(db.Model):
    __table_args__ = (
        UniqueConstraint("name", "owner_id", name='ux__folder__name__owner_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))

    owner_id = db.Column(db.Integer, db.ForeignKey(User.id))
    owner = db.relationship(User, backref=db.backref("folders", cascade="all,delete")) 

    shared_users = db.relationship(User, secondary=folders__shared_users, backref=db.backref("shared_folders"), collection_class=set)

    @property
    def publication_count(self):
        return Publication.query.filter(Publication.folders.any(Folder.id == self.id)).count()


class FolderDoi(db.Model):
    __table_args__ = (
        UniqueConstraint("folder_id", "doi", name='ux__folder_doi__folder_id__doi'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    folder_id = mapped_column(ForeignKey(Folder.id), nullable=False, index=True)
    folder: Mapped[Folder] = relationship(
        foreign_keys=[folder_id],
        backref=backref(
            "dois",
            collection_class=set,
        )
    )
    doi: Mapped[str] = mapped_column(Unicode(1000), nullable=False)
    publication: Mapped[Folder] = relationship(
        Publication,
        foreign_keys=[doi],
        primaryjoin='FolderDoi.doi == Publication.doi',
        backref=backref(
            "folder_dois",
            collection_class=set,
        )
    )

    @property
    def invalid_doi(self):
        return is_invalid_doi(self.doi)