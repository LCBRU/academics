#!/usr/bin/env python3

from dotenv import load_dotenv
from lbrc_flask.database import db


load_dotenv()

from academics import create_app

application = create_app()
application.app_context().push()
db.create_all()
db.session.close()
