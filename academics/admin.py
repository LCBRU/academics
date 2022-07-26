import datetime
from flask_admin.contrib.sqla import fields
from lbrc_flask.database import db
from lbrc_flask.security import Role, User
from lbrc_flask.admin import AdminCustomView, init_admin as flask_init_admin
from flask_login import current_user

from academics.model import Theme


class QuerySelectMultipleFieldSet(fields.QuerySelectMultipleField):
    def populate_obj(self, obj, name):
        setattr(obj, name, set(self.data))


class UserView(AdminCustomView):
    column_list = ["username", "first_name", "last_name", "active", "roles"]
    form_columns = ["username", "roles"]

    # form_args and form_overrides required to allow roles to be sets.
    form_args = {
        'roles': {
            'query_factory': lambda: db.session.query(Role)
        },
    }


class ThemeView(AdminCustomView):
    column_list = ['name']
    form_columns = ["name"]

    # def on_model_change(self, form, model, is_created):
    #     model.last_updated_datetime = datetime.datetime.utcnow()
    #     model.last_updated_by_user = current_user


def init_admin(app, title):
    flask_init_admin(
        app,
        title,
        [
            UserView(User, db.session),
            ThemeView(Theme, db.session),
        ]
    )
