from lbrc_flask.security import AuditMixin
from lbrc_flask.database import db
from academics.model.theme import Theme


class Objective(db.Model, AuditMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))
    completed = db.Column(db.Boolean, default=False)

    theme_id = db.Column(db.Integer, db.ForeignKey(Theme.id))
    theme = db.relationship(Theme, backref=db.backref("objectives", cascade="all,delete"))
