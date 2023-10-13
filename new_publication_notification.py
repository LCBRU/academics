#!/usr/bin/env python3

from dotenv import load_dotenv
from flask import render_template
from sqlalchemy import select
from lbrc_flask.database import db
from lbrc_flask.emailing import email

from academics.model import ScopusPublication
from academics import create_app

# Load environment variables from '.env' file.
load_dotenv()
application = create_app()
application.app_context().push()

q = select(ScopusPublication)

publications = list(db.session.execute(q).unique().scalars())

email(
    subject='New Publications this Month',
    message=render_template('email/new_publications.txt', publications=publications),
    recipients=[],
    html_template='email/new_publications.html',
    publications=publications,
)