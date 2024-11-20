#!/usr/bin/env python3

import os
from lbrc_flask.database import db

# Load environment variables from '.env' file.
from dotenv import load_dotenv

from academics.jobs.publications import AutoFillFolders, PublicationRemoveUnused
load_dotenv()

from academics.jobs.catalogs import RefreshAll

from academics import create_app
from lbrc_flask.async_jobs import AsyncJobs, run_jobs_asynch

application = create_app()
application.app_context().push()

application.config['SERVER_NAME'] = os.environ["CELERY_SERVER_NAME"]

AsyncJobs.schedule(RefreshAll())
AsyncJobs.schedule(PublicationRemoveUnused())
AsyncJobs.schedule(AutoFillFolders())

db.session.commit()
run_jobs_asynch()
