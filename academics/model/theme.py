from sqlalchemy import UniqueConstraint
from lbrc_flask.security import AuditMixin
from lbrc_flask.model import CommonMixin
from lbrc_flask.database import db


class Theme(AuditMixin, CommonMixin, db.Model):
    DEFAULT_VALUES = [
        {'name': 'Cardiology'},
        {'name': 'Lifestyle'},
        {'name': 'Respirator'},
        {'name': 'Precision Medicine'},
        {'name': 'Cancer'},
        {'name': 'Data MLTcs Ethnic Health'},
        {'name': 'Environment'},
    ]

    __table_args__ = (
        UniqueConstraint("name", name='ux__theme__name'),
    )

    id = db.Column(db.Integer, primary_key=True)
    # MariaDB backends need a VARChar variable, added 255 to set a max length
    name = db.Column(db.String(255))

    def __str__(self):
        return self.name or ""

