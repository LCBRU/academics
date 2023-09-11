from flask import Blueprint
from lbrc_flask.database import db
from lbrc_flask.api import validate_api_key


blueprint = Blueprint("api", __name__, template_folder="templates")

# Login required for all views
@blueprint.before_request
@validate_api_key()
def before_request():
    pass


@blueprint.record
def record(state):
    if db is None:
        raise Exception(
            "This blueprint expects you to provide " "database access through database"
        )


from .views import *
