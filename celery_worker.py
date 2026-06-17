#!/usr/bin/env python3

import os
from dotenv import load_dotenv
import urllib3
from flask import g

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables from '.env' file.
load_dotenv()

from academics import create_app

application = create_app()
application.app_context().push()
g.lbrc_flask_title = 'Academics Celery Worker'


application.config['SERVER_NAME'] = os.environ["CELERY_SERVER_NAME"]

from lbrc_flask.celery import celery