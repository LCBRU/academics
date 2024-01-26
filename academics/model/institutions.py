from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.orm import backref
from lbrc_flask.database import db

from academics.model.publication import Publication
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref


institutions__publications = db.Table(
    'institutions__publications',
    db.Column('institution_id', db.Integer(), db.ForeignKey('institution.id'), primary_key=True),
    db.Column('publication_id', db.Integer(), db.ForeignKey('publication.id'), primary_key=True),
)


class Institution(db.Model):
    __table_args__ = (
        UniqueConstraint("name", name='ux__institution__name'),
        UniqueConstraint("catalog", "catalog_identifier", name='ux__institution__catalog__catalog_identifier'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    catalog: Mapped[str] = mapped_column(String(100), nullable=False)
    catalog_identifier: Mapped[str] = mapped_column(String(1000), nullable=False)
    name: Mapped[str] = mapped_column(String(1000), nullable=False)
    country_code: Mapped[str] = mapped_column(String(10), nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    refresh_full_details: Mapped[bool] = mapped_column(Boolean, nullable=True)

    publications: Mapped[Publication] = relationship(
        "Publication",
        secondary=institutions__publications,
        collection_class=set,
        backref=backref(
            "institutions",
            collection_class=set,
        )
    )
