#!/usr/bin/env python3

import os
from dotenv import load_dotenv

# Load environment variables from '.env' file.
load_dotenv()

from academics import create_app
from academics.scopus.service import update_academics

application = create_app()
application.app_context().push()

application.config['SERVER_NAME'] = os.environ["CELERY_SERVER_NAME"]

update_academics()
