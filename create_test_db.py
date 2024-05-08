#!/usr/bin/env python3

import random
import string
from dotenv import load_dotenv
from lbrc_flask.database import db
from lbrc_flask.security import init_roles, init_users
from academics.model.academic import Academic, Affiliation, CatalogPublicationsSources, Source
from academics.model.publication import *
from academics.model.theme import Theme
from academics.security import ROLE_EDITOR, ROLE_VALIDATOR, get_roles


load_dotenv()

from academics import create_app

application = create_app()
application.app_context().push()
db.drop_all()
db.create_all()
init_roles(get_roles())
init_users(admin_roles=[ROLE_VALIDATOR, ROLE_EDITOR])

# Sub Types
for st in ['article', 'book', 'correction']:
    db.session.add(Subtype(code=st, description=st))
db.session.commit()

# Themes
for t in ['Theme 1', 'Theme 2']:
    db.session.add(Theme(name=t))
db.session.commit()

# Journal
for j in ['Journal 1', 'Journal 2']:
    db.session.add(Journal(name=j))
db.session.commit()

# Sponsor
for s in ['Sponsor 1', 'Sponsor 2']:
    db.session.add(Sponsor(name=s))
db.session.commit()

acknowledgement_details = {
    'NIHR Acknowledged': True,
    'BRC Investigators Not A Primary Author': False,
    'Need Senior Review': False,
    'NIHR Not Acknowledged': False,
    'No BRC Investigator On Publication Or Not Relevanr': False,
    'Unable To Check - Full Paper Not Available': False,    
}

# Acknowledgement
for n, a in acknowledgement_details.items():
    db.session.add(NihrAcknowledgement(name=n, acknowledged=a))
db.session.commit()

# Keyword
for k in ['Keyword 1', 'Keyword 2', 'Keyword 3']:
    db.session.add(Keyword(keyword=k))

db.session.commit()

# Affiliations
for a in ['Affiliation 1', 'Affiliation 2', 'Affiliation 3', 'Affiliation 4', 'Affiliation 5', 'Affiliation 6']:
    db.session.add(Affiliation(name=a))

db.session.commit()

all_affiliations = db.session.execute(select(Affiliation)).scalars().all()

# Academic
for a in [
    {
        'first_name': 'Fred',
        'last_name': 'Hoyle',
        'themes': [1],
    },
    {
        'first_name': 'Richard',
        'last_name': 'Feynman',
        'themes': [1,2],
    },
    {
        'first_name': 'Peter',
        'last_name': 'Faulk',
        'themes': [2],
    },
]:
    aca = Academic(first_name=a['first_name'], last_name=a['last_name'], initialised=True)
    aca.themes = db.session.execute(select(Theme).where(Theme.id.in_(a['themes']))).scalars().all()
    db.session.add(aca)

db.session.commit()

for a in [
    {
        'academic_id': 1,
        'first_name': 'Fred',
        'last_name': 'Hoyle',
        'display_name': 'Fred Hoyle',
        'catalog': CATALOG_SCOPUS,
        'catalog_identifier': '12345678',
        'citation_count': random.randint(1, 1000),
        'document_count': random.randint(1, 1000),
        'h_index': random.randint(1, 100),
        'affiliations': random.sample(all_affiliations, random.randint(1, len(all_affiliations))),
        'orcid': ''.join(random.choices(string.ascii_uppercase + string.digits, k=random.randint(10, 15))),
    },
    {
        'academic_id': 1,
        'first_name': 'Frederick',
        'last_name': 'Hoyle',
        'display_name': 'Frederick Hoyle',
        'catalog': CATALOG_SCOPUS,
        'catalog_identifier': '23456789',
        'citation_count': random.randint(1, 1000),
        'document_count': random.randint(1, 1000),
        'h_index': random.randint(1, 100),
        'affiliations': random.sample(all_affiliations, random.randint(1, len(all_affiliations))),
        'orcid': ''.join(random.choices(string.ascii_uppercase + string.digits, k=random.randint(10, 15))),
    },
    {
        'academic_id': 2,
        'first_name': 'Richard',
        'last_name': 'Feynman',
        'display_name': 'Richard Feynman',
        'catalog': CATALOG_SCOPUS,
        'catalog_identifier': '34567890',
        'citation_count': random.randint(1, 1000),
        'document_count': random.randint(1, 1000),
        'h_index': random.randint(1, 100),
        'affiliations': random.sample(all_affiliations, random.randint(1, len(all_affiliations))),
        'orcid': ''.join(random.choices(string.ascii_uppercase + string.digits, k=random.randint(10, 15))),
    },
    {
        'academic_id': 2,
        'first_name': 'Dicky',
        'last_name': 'Feynman',
        'display_name': 'Dicky Feynman',
        'catalog': CATALOG_SCOPUS,
        'catalog_identifier': '45678901',
        'citation_count': random.randint(1, 1000),
        'document_count': random.randint(1, 1000),
        'h_index': random.randint(1, 100),
        'affiliations': random.sample(all_affiliations, random.randint(1, len(all_affiliations))),
        'orcid': ''.join(random.choices(string.ascii_uppercase + string.digits, k=random.randint(10, 15))),
    },
    {
        'academic_id': 3,
        'first_name': 'Peter',
        'last_name': 'Faulk',
        'display_name': 'Peter Faulk',
        'catalog': CATALOG_SCOPUS,
        'catalog_identifier': '56789012',
        'citation_count': random.randint(1, 1000),
        'document_count': random.randint(1, 1000),
        'h_index': random.randint(1, 100),
        'affiliations': random.sample(all_affiliations, random.randint(1, len(all_affiliations))),
        'orcid': ''.join(random.choices(string.ascii_uppercase + string.digits, k=random.randint(10, 15))),
    },
    {
        'academic_id': 3,
        'first_name': 'Pete',
        'last_name': 'Faulk',
        'display_name': 'Peter Faulk',
        'catalog': CATALOG_SCOPUS,
        'catalog_identifier': '67890123',
        'citation_count': random.randint(1, 1000),
        'document_count': random.randint(1, 1000),
        'h_index': random.randint(1, 100),
        'affiliations': random.sample(all_affiliations, random.randint(1, len(all_affiliations))),
        'orcid': ''.join(random.choices(string.ascii_uppercase + string.digits, k=random.randint(10, 15))),
    },
    {
        'first_name': 'Other',
        'last_name': 'Author',
        'display_name': 'Other Author',
        'catalog': CATALOG_SCOPUS,
        'catalog_identifier': '78901234',
        'citation_count': random.randint(1, 1000),
        'document_count': random.randint(1, 1000),
        'h_index': random.randint(1, 100),
        'affiliations': random.sample(all_affiliations, random.randint(1, len(all_affiliations))),
        'orcid': ''.join(random.choices(string.ascii_uppercase + string.digits, k=random.randint(10, 15))),
    },
]:
    db.session.add(Source(**a))

db.session.commit()

for pd in [
    {
        'sources': [1, 7],
        'title': 'Lorem ipsum dolor sit amet.',
        'publication_cover_date': '2023-01-01',
        'catalog_identifier': '111',
        'doi': '10.10.01',
        'journal_id': 1,
        'keywords': [1],
    },
    {
        'sources': [2, 7],
        'title': 'Nunc ullamcorper mauris vitae neque dictum facilisis',
        'publication_cover_date': '2023-01-02',
        'catalog_identifier': '112',
        'doi': '10.10.02',
        'journal_id': 1,
        'keywords': [1,2],
    },
    {
        'sources': [2, 7],
        'title': 'Nam tristique ex in tempus molestie',
        'publication_cover_date': '2023-01-03',
        'catalog_identifier': '113',
        'doi': '10.10.03',
        'journal_id': 1,
        'keywords': [2],
    },
    {
        'sources': [3, 7],
        'title': 'Sed rutrum velit quis lectus dapibus, in dignissim turpis rutrum',
        'publication_cover_date': '2023-01-04',
        'catalog_identifier': '114',
        'doi': '10.10.04',
        'journal_id': 1,
        'keywords': [2,3],
    },
    {
        'sources': [3, 7],
        'title': 'Suspendisse quis magna aliquet, scelerisque mauris at, sollicitudin purus.',
        'publication_cover_date': '2023-01-05',
        'catalog_identifier': '115',
        'doi': '10.10.05',
        'journal_id': 1,
        'keywords': [3],
    },
    {
        'sources': [3, 7],
        'title': 'Morbi feugiat ex ut ante luctus, sed mattis turpis vehicula',
        'publication_cover_date': '2023-01-06',
        'catalog_identifier': '116',
        'doi': '10.10.06',
        'journal_id': 1,
        'keywords': [1,2,3],
    },
    {
        'sources': [4, 7],
        'title': 'Curabitur nec augue vel nulla elementum molestie nec eu odio',
        'publication_cover_date': '2023-01-07',
        'catalog_identifier': '117',
        'doi': '10.10.07',
        'journal_id': 1,
        'keywords': [1],
    },
    {
        'sources': [4, 7],
        'title': 'Fusce ut lectus fermentum, luctus mauris at, posuere arcu',
        'publication_cover_date': '2023-01-08',
        'catalog_identifier': '118',
        'doi': '10.10.08',
        'journal_id': 1,
        'keywords': [1,2],
    },
    {
        'sources': [4, 7],
        'title': 'Donec finibus nunc in lectus ullamcorper, dictum euismod neque fermentum',
        'publication_cover_date': '2023-01-09',
        'catalog_identifier': '119',
        'doi': '10.10.09',
        'journal_id': 1,
        'keywords': [2],
    },
    {
        'sources': [4, 7],
        'title': 'Ut et ipsum ut neque fermentum efficitur non sed felis',
        'publication_cover_date': '2023-01-10',
        'catalog_identifier': '121',
        'doi': '10.10.10',
        'journal_id': 1,
        'keywords': [2,3],
    },
    {
        'sources': [5, 7],
        'title': 'Ut tempus ante et odio tempor, et finibus mauris mattis',
        'publication_cover_date': '2023-02-01',
        'catalog_identifier': '131',
        'doi': '10.10.11',
        'journal_id': 1,
        'keywords': [3],
    },
    {
        'sources': [5, 7],
        'title': 'Vestibulum suscipit ipsum a massa feugiat molestie',
        'publication_cover_date': '2023-02-03',
        'catalog_identifier': '141',
        'doi': '10.10.12',
        'journal_id': 1,
        'keywords': [1,2,3],
    },
    {
        'sources': [5, 7],
        'title': 'Cras ullamcorper nisi vel libero volutpat, quis accumsan tellus rhoncus',
        'publication_cover_date': '2023-03-01',
        'catalog_identifier': '151',
        'doi': '10.10.13',
        'journal_id': 1,
        'keywords': [1],
    },
    {
        'sources': [5, 7],
        'title': 'Nunc id tellus sit amet massa sollicitudin pellentesque in sit amet velit',
        'publication_cover_date': '2023-03-02',
        'catalog_identifier': '161',
        'doi': '10.10.14',
        'journal_id': 2,
        'keywords': [1,2],
    },
    {
        'sources': [5, 7],
        'title': 'Sed id sapien convallis, ornare diam ac, egestas lacus',
        'publication_cover_date': '2023-03-03',
        'catalog_identifier': '171',
        'doi': '10.10.15',
        'journal_id': 2,
        'keywords': [1,3],
    },
    {
        'sources': [6, 7],
        'title': 'Ut viverra dolor eu quam viverra egestas',
        'publication_cover_date': '2023-01-11',
        'catalog_identifier': '181',
        'doi': '10.10.16',
        'journal_id': 2,
        'keywords': [2],
    },
    {
        'sources': [6, 7],
        'title': 'Aliquam rhoncus orci sed lectus iaculis, ut tempus diam iaculis',
        'publication_cover_date': '2023-01-12',
        'catalog_identifier': '191',
        'doi': '10.10.17',
        'journal_id': 2,
        'keywords': [2,3],
    },
    {
        'sources': [6, 7],
        'title': 'Donec auctor risus ut velit faucibus cursus',
        'publication_cover_date': '2023-01-13',
        'catalog_identifier': '211',
        'doi': '10.10.18',
        'journal_id': 2,
        'keywords': [3],
    },
    {
        'sources': [6, 7],
        'title': 'Quisque commodo sapien vel lectus commodo, eu molestie sapien blandit',
        'publication_cover_date': '2023-01-14',
        'catalog_identifier': '311',
        'doi': '10.10.19',
        'journal_id': 2,
        'keywords': [1,2,3],
    },
    {
        'sources': [6, 7],
        'title': 'Nullam malesuada erat quis consequat tempus',
        'publication_cover_date': '2023-01-15',
        'catalog_identifier': '411',
        'doi': '10.10.20',
        'journal_id': 2,
        'keywords': [1],
    },
    {
        'sources': [6, 7],
        'title': 'Integer feugiat tortor ut commodo interdum',
        'publication_cover_date': '2023-01-16',
        'catalog_identifier': '511',
        'doi': '10.10.21',
        'journal_id': 2,
        'keywords': [1,2],
    },
]:

    cp = CatalogPublication(
        catalog=CATALOG_SCOPUS,
        catalog_identifier=pd['catalog_identifier'],
        title=pd['title'],
        publication_cover_date=pd['publication_cover_date'],
        subtype_id=1,
        publication=Publication(doi=pd['doi']),
        doi=pd['doi'],
        abstract='',
        volume='',
        issue='',
        pages='',
        funding_text='',
        href='',
        journal_id=pd['journal_id'],
    )

    cp.keywords = set(db.session.execute(select(Keyword).where(Keyword.id.in_(pd['keywords']))).scalars().all())

    for s in pd['sources']:
        cp.catalog_publication_sources.append(CatalogPublicationsSources(
            catalog_publication=cp,
            source=db.session.get(Source, s),
        ))
        db.session.add(cp)

db.session.commit()

db.session.close()

from alembic.config import Config
from alembic import command
alembic_cfg = Config("alembic.ini")
command.stamp(alembic_cfg, "head")
