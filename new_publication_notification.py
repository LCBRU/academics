#!/usr/bin/env python3

from datetime import date
from dateutil.relativedelta import relativedelta 
from dotenv import load_dotenv
from flask import render_template
from sqlalchemy import select
from lbrc_flask.database import db
from lbrc_flask.emailing import email
from lbrc_flask.security import get_users_for_role
from academics.security import ROLE_NEW_PUBLICATION_RECIPIENT

from academics.model import ScopusPublication
from academics import create_app

# Load environment variables from '.env' file.
load_dotenv()
application = create_app()
application.app_context().push()

today = date.today()
this_month_start = date(today.year, today.month, 1)
last_month_start = this_month_start - relativedelta(months=1)

q = (
    select(ScopusPublication)
    .where(ScopusPublication.created_date.between(last_month_start, this_month_start))
    .order_by(ScopusPublication.created_date.asc)
)

publications = list(db.session.execute(q).unique().scalars())

recipients = get_users_for_role(ROLE_NEW_PUBLICATION_RECIPIENT)

email(
    subject='New Publications this Month',
    message=render_template('email/new_publications.txt', publications=publications),
    recipients=[],
    html_template='email/new_publications.html',
    publications=publications,
)