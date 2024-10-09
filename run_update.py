#!/usr/bin/env python3

import os

# Load environment variables from '.env' file.
from dotenv import load_dotenv
load_dotenv()

from academics.catalogs.jobs import RefreshAll

from academics import create_app
from lbrc_flask.async_jobs import AsyncJobs

application = create_app()
application.app_context().push()

application.config['SERVER_NAME'] = os.environ["CELERY_SERVER_NAME"]

AsyncJobs.schedule(RefreshAll())
