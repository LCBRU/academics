from lbrc_flask.database import db
from academics.jobs.catalogs import PublicationReGuessStatus, RefreshAll
from flask_security import roles_accepted
from lbrc_flask.async_jobs import AsyncJobs, run_jobs_asynch
from lbrc_flask.response import refresh_response

from academics.jobs.publications import AutoFillFolders
from .. import blueprint


@blueprint.route("/jobs/update_all_academics")
@roles_accepted('admin')
def update_all_academics():
    AsyncJobs.schedule(RefreshAll())
    db.session.commit()
    
    run_jobs_asynch()
    return refresh_response()


@blueprint.route("/jobs/run_outstanding_jobs")
@roles_accepted('admin')
def run_outstanding_jobs():
    run_jobs_asynch()
    return refresh_response()


@blueprint.route("/jobs/fill_folders")
@roles_accepted('admin')
def auto_fill_folders():
    AsyncJobs.schedule(AutoFillFolders())
    db.session.commit()
    
    run_jobs_asynch()
    return refresh_response()


@blueprint.route("/redo_publication_statuses")
@roles_accepted('admin')
def redo_publication_statuses():
    AsyncJobs.schedule(PublicationReGuessStatus())
    db.session.commit()

    run_jobs_asynch()
    return refresh_response()
