#!/usr/bin/env python3

import json
from datetime import date
from dotenv import load_dotenv
from flask import current_app
from academics import create_app
from sqlalchemy import select
from lbrc_flask.database import db

from academics.model.publication import CatalogPublication

# Load environment variables from '.env' file.
load_dotenv()

from academics.catalogs.scopus import ScopusClient, get_scopus_publication_data

application = create_app()
application.app_context().push()

# out = get_scopus_publication_data(doi=sys.argv[1], log_data=True)

client = ScopusClient(current_app.config['SCOPUS_API_KEY'])

q = select(CatalogPublication).where(CatalogPublication.publication_cover_date == date(day=1, month=1, year=2023))

details = []

for p in list(db.session.execute(q).scalars())[:1]:
    uri=f'https://api.elsevier.com/content/abstract/doi/{p.doi}'

    details.append(client.exec_request(uri))

with open('scopus_date_check.json', 'w', encoding='utf-8') as f:
    json.dump(details, f, ensure_ascii=False, indent=4)
