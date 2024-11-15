from sqlalchemy import Boolean, ForeignKey, Integer, String, Unicode, UniqueConstraint, func, select
from sqlalchemy.orm import backref
from lbrc_flask.database import db
from lbrc_flask.validators import is_invalid_doi
from academics.model.publication import Publication
from academics.model.security import User
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref, column_property
from lbrc_flask.security import AuditMixin
from lbrc_flask.model import CommonMixin


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
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    autofill_year: Mapped[int] = mapped_column(Integer, nullable=True)
    author_access: Mapped[bool] = mapped_column(Boolean, nullable=True)

    owner_id = db.Column(db.Integer, db.ForeignKey(User.id))
    owner = db.relationship(User, backref=db.backref("folders", cascade="all,delete")) 
    shared_users = db.relationship(User, secondary=folders__shared_users, backref=db.backref("shared_folders"), collection_class=set, lazy="selectin")

    def can_user_edit(self, user):
        return user == self.owner or user in self.shared_users


class FolderDoi(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    folder_id = mapped_column(ForeignKey(Folder.id), nullable=False, index=True)
    folder: Mapped[Folder] = relationship(
        foreign_keys=[folder_id],
        backref=backref(
            "dois",
            collection_class=set,
            cascade="all, delete",
        )
    )
    deleted: Mapped[bool] = mapped_column(Boolean)
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


Folder.publication_count = column_property(
        select(func.count(FolderDoi.doi))
        .where(FolderDoi.folder_id == Folder.id)
        .correlate_except(FolderDoi)
        .scalar_subquery()
    )


class FolderDoiUserRelevance(AuditMixin, CommonMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    folder_doi_id = mapped_column(ForeignKey(FolderDoi.id), nullable=False, index=True)
    folder_doi: Mapped[FolderDoi] = relationship(
        foreign_keys=[folder_doi_id],
        backref=backref(
            "user_statuses",
            collection_class=set,
            cascade="all, delete",
        )
    )
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id), nullable=False, index=True)
    user: Mapped[User] = relationship(foreign_keys=[user_id])

    relevant: Mapped[bool] = mapped_column(Boolean)
