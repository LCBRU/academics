from sqlalchemy import Boolean, String, UniqueConstraint
from lbrc_flask.database import db
from sqlalchemy.orm import Mapped, mapped_column


class Institution(db.Model):
    __table_args__ = (
        UniqueConstraint("name", name='ux__institution__name'),
        UniqueConstraint("catalog", "catalog_identifier", name='ux__institution__catalog__catalog_identifier'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    catalog: Mapped[str] = mapped_column(String(100), nullable=False)
    catalog_identifier: Mapped[str] = mapped_column(String(500), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    country_code: Mapped[str] = mapped_column(String(10), nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    refresh_full_details: Mapped[bool] = mapped_column(Boolean, nullable=True)
    home_institution: Mapped[bool] = mapped_column(Boolean, nullable=True)
