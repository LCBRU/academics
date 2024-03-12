import datetime
from flask_admin.contrib.sqla import fields
from lbrc_flask.database import db
from lbrc_flask.security import Role
from lbrc_flask.admin import AdminCustomView, init_admin as flask_init_admin
from lbrc_flask.api import ApiKey
from academics.model.publication import Journal

from academics.model.security import User
from academics.model.theme import Theme


class QuerySelectMultipleFieldSet(fields.QuerySelectMultipleField):
    def populate_obj(self, obj, name):
        setattr(obj, name, set(self.data))


class UserView(AdminCustomView):
    column_list = ["username", "first_name", "last_name", "active", "roles"]
    form_columns = ["username", "roles", "theme"]

    # form_args and form_overrides required to allow roles to be sets.
    form_args = {
        'roles': {
            'query_factory': lambda: db.session.query(Role)
        },
    }


class ThemeView(AdminCustomView):
    form_columns = column_list = ['name']


class JournalView(AdminCustomView):
    column_list = form_columns = ["name", 'preprint']
    


class ApiKeyView(AdminCustomView):
    column_list = ['name', 'key']
    form_columns = ["name"]


def init_admin(app, title):
    flask_init_admin(
        app,
        title,
        [
            UserView(User, db.session),
            ThemeView(Theme, db.session),
            JournalView(Journal, db.session),
            ApiKeyView(ApiKey, db.session),
        ]
    )
