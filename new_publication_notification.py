#!/usr/bin/env python3

# Load environment variables from '.env' file.
from dotenv import load_dotenv
load_dotenv()

import argparse
from datetime import date, timedelta
from flask import render_template
from sqlalchemy import select
from lbrc_flask.database import db
from lbrc_flask.emailing import email
from lbrc_flask.security import get_users_for_role
from academics.security import ROLE_NEW_PUBLICATION_RECIPIENT

from academics.model.publication import CatalogPublication, Publication
from academics import create_app

parser = argparse.ArgumentParser()
parser.add_argument("-w", "--weeks", help="Number of previous weeks to report on", type=int, default=1)
args = parser.parse_args()
weeks = args.weeks

application = create_app()
application.app_context().push()

today = date.today()
last_week_end = today - timedelta(days=today.weekday() + 1)
last_week_start = last_week_end - timedelta(days=6)
if weeks > 1:
    last_week_start -= timedelta(weeks=weeks-1)

q = (
    select(Publication)
    .where(Publication.catalog_publications.any(CatalogPublication.publication_cover_date.between(last_week_start, last_week_end)))
)

publications = list(db.session.execute(q).unique().scalars())

email(
    subject='New Publications Last Week',
    message=render_template('email/new_publications.txt', publications=publications),
    recipients=[u.email for u in get_users_for_role(ROLE_NEW_PUBLICATION_RECIPIENT)],
    # recipients=['rab63@leicester.ac.uk'],
    html_template='email/new_publications.html',
    publications=publications,
)
