from flask_admin.contrib.sqla import fields
from lbrc_flask.database import db
from lbrc_flask.security import Role, User
from lbrc_flask.admin import AdminCustomView, init_admin as flask_init_admin


class QuerySelectMultipleFieldSet(fields.QuerySelectMultipleField):
    def populate_obj(self, obj, name):
        setattr(obj, name, set(self.data))


class UserView(AdminCustomView):
    column_list = form_columns = ["username", "first_name", "last_name", "active", "roles"]

    # form_args and form_overrides required to allow roles to be sets.
    form_args = {
        'roles': {
            'query_factory': lambda: db.session.query(Role)
        },
    }
    form_overrides = {
        'roles': QuerySelectMultipleFieldSet,
    }


def init_admin(app, title):
    flask_init_admin(
        app,
        title,
        [
            UserView(User, db.session),
        ]
    )
