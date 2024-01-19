from lbrc_flask.database import db
from lbrc_flask.security import User as BaseUser
from academics.model.theme import Theme


class User(BaseUser):
    __table_args__ = {'extend_existing': True}

    theme_id = db.Column(db.Integer, db.ForeignKey(Theme.id))
    theme = db.relationship(Theme, lazy='joined')


