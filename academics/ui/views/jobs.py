from lbrc_flask.database import db
from academics.jobs.catalogs import RefreshAll
from flask_security import roles_accepted
from lbrc_flask.async_jobs import AsyncJobs, run_jobs_asynch
from lbrc_flask.response import refresh_response
from .. import blueprint


@blueprint.route("/update_all_academics")
@roles_accepted('admin')
def update_all_academics():
    AsyncJobs.schedule(RefreshAll())
    db.session.commit()
    
    run_jobs_asynch()
    return refresh_response()


@blueprint.route("/trigger_refresh")
@roles_accepted('admin')
def trigger_refresh():
    run_jobs_asynch()
    return refresh_response()
