#!/usr/bin/env python3

from dotenv import load_dotenv
from lbrc_flask.database import db
from lbrc_flask.security import init_roles, init_users
from academics.security import get_roles


load_dotenv()

from academics import create_app

application = create_app()
application.app_context().push()
db.create_all()
init_roles(get_roles())
init_users()
db.session.close()
