from sqlalchemy import String, TEXT
from lbrc_flask.database import db
from sqlalchemy.orm import Mapped, mapped_column
from lbrc_flask.security import AuditMixin
from lbrc_flask.model import CommonMixin


class RawData(AuditMixin, CommonMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    catalog: Mapped[str] = mapped_column(String(100), nullable=False)
    catalog_identifier: Mapped[str] = mapped_column(String(500), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_text: Mapped[str] = mapped_column(TEXT, nullable=True)
