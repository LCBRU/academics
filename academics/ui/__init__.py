from flask.blueprints import Blueprint
from flask_security import login_required
from lbrc_flask.database import db


blueprint = Blueprint("ui", __name__, template_folder="templates")

# Login required for all views
@blueprint.before_request
@login_required
def before_request():
    pass


@blueprint.record
def record(state):
    if db is None:
        raise Exception(
            "This blueprint expects you to provide " "database access through database"
        )


from .views import *
