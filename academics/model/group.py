from typing import List
from sqlalchemy import ForeignKey, String, UniqueConstraint
from lbrc_flask.database import db
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
from academics.model.academic import Academic
from academics.model.security import User


groups__shared_users = db.Table(
    'groups__shared_users',
    db.Column('group_id', db.Integer(), db.ForeignKey('group.id'), primary_key=True),
    db.Column('user_id', db.Integer(), db.ForeignKey(User.id), primary_key=True),
)

groups__academics = db.Table(
    'groups__academics',
    db.Column('group_id', db.Integer(), db.ForeignKey('group.id'), primary_key=True),
    db.Column('academic_id', db.Integer(), db.ForeignKey(Academic.id), primary_key=True),
)

class Group(db.Model):
    __table_args__ = (
        UniqueConstraint("name", "owner_id", name='ux__group__name__owner_id'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    owner_id = mapped_column(ForeignKey(User.id), nullable=False, index=True)
    owner: Mapped[User] = relationship(foreign_keys=[owner_id])
    shared_users: Mapped[List[User]] = relationship(secondary=groups__shared_users, collection_class=set)
    academics: Mapped[List[Academic]] = relationship(
        secondary=groups__academics,
        collection_class=set,
        backref=backref(
            "groups",
            collection_class=set,
        )
    )
