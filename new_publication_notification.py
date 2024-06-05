#!/usr/bin/env python3

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta 
from dotenv import load_dotenv
from flask import render_template
from sqlalchemy import select
from lbrc_flask.database import db
from lbrc_flask.emailing import email
from lbrc_flask.security import get_users_for_role
from academics.security import ROLE_NEW_PUBLICATION_RECIPIENT

from academics.model.publication import CatalogPublication, Publication
from academics import create_app

from dateutil.parser import parse

# Load environment variables from '.env' file.
load_dotenv()
application = create_app()
application.app_context().push()

today = date.today()
last_week_end = today - timedelta(days=today.weekday() + 1)
last_week_start = last_week_end - timedelta(days=6)

print(last_week_end)
print(last_week_start)

q = (
    select(Publication)
    .where(Publication.catalog_publications.any(CatalogPublication.publication_cover_date.between(last_week_start, last_week_end)))
)

print(q)

publications = list(db.session.execute(q).unique().scalars())

print(publications)

email(
    subject='New Publications Last Week',
    message=render_template('email/new_publications.txt', publications=publications),
    recipients=[u.email for u in get_users_for_role(ROLE_NEW_PUBLICATION_RECIPIENT)],
    # recipients=['rab63@leicester.ac.uk'],
    html_template='email/new_publications.html',
    publications=publications,
)
