from lbrc_flask.database import db
from academics.jobs.catalogs import ManaualCatalogPublicationsFindScopus, PublicationReGuessStatus, RefreshAll, InstitutionRefreshAll
from flask_security import roles_accepted
from lbrc_flask.async_jobs import AsyncJobs, run_jobs_asynch
from lbrc_flask.response import refresh_response

from academics.jobs.publications import AutoFillFolders
from academics.services.publication_searching import manual_only_catalog_publications
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


@blueprint.route("/jobs/manaual_catalog_publications_find_scopus")
@roles_accepted('admin')
def manaual_catalog_publications_find_scopus():
    AsyncJobs.schedule(ManaualCatalogPublicationsFindScopus())
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


@blueprint.route("/refresh_institutions")
@roles_accepted('admin')
def refresh_institutions():
    AsyncJobs.schedule(InstitutionRefreshAll())
    db.session.commit()

    run_jobs_asynch()
    return refresh_response()
