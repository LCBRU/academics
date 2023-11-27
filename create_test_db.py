#!/usr/bin/env python3

from dotenv import load_dotenv
from lbrc_flask.database import db
from lbrc_flask.security import init_roles, init_users
from academics.model import *
from academics.security import get_roles


load_dotenv()

from academics import create_app

application = create_app()
application.app_context().push()
db.create_all()
init_roles(get_roles())
init_users()

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

# Acknowledgement
for n, a in NihrAcknowledgement.all_details.items():
    db.session.add(NihrAcknowledgement(name=n, acknowledged=a))
db.session.commit()

# Keyword
for k in ['Keyword 1', 'Keyword 2']:
    db.session.add(Keyword(keyword=k))
db.session.commit()

# Academic
for a in [
    {
        'first_name': 'Fred',
        'last_name': 'Hoyle',
        'theme_id': 1,
    },
    {
        'first_name': 'Richard',
        'last_name': 'Feynman',
        'theme_id': 1,
    },
    {
        'first_name': 'Peter',
        'last_name': 'Faulk',
        'theme_id': 2,
    },
]:
    db.session.add(Academic(**a, initialised=True))
db.session.commit()

# ScopusAuthor
for a in [
    {
        'academic_id': 1,
        'first_name': 'Fred',
        'last_name': 'Hoyle',
    },
    {
        'academic_id': 1,
        'first_name': 'Frederick',
        'last_name': 'Hoyle',
    },
    {
        'academic_id': 2,
        'first_name': 'Richard',
        'last_name': 'Feynman',
    },
    {
        'academic_id': 2,
        'first_name': 'Dicky',
        'last_name': 'Feynman',
    },
    {
        'academic_id': 3,
        'first_name': 'Peter',
        'last_name': 'Faulk',
    },
    {
        'academic_id': 3,
        'first_name': 'Pete',
        'last_name': 'Faulk',
    },
]:
    db.session.add(ScopusAuthor(**a))
db.session.commit()

for p in [
    {
        'scopus_author_id': 1,
        'title': 'Lorem ipsum dolor sit amet.',
        'publication_cover_date': '2023-01-01',
    },
    {
        'scopus_author_id': 2,
        'title': 'Nunc ullamcorper mauris vitae neque dictum facilisis',
        'publication_cover_date': '2023-01-02',
    },
    {
        'scopus_author_id': 2,
        'title': 'Nam tristique ex in tempus molestie',
        'publication_cover_date': '2023-01-03',
    },
    {
        'scopus_author_id': 3,
        'title': 'Sed rutrum velit quis lectus dapibus, in dignissim turpis rutrum',
        'publication_cover_date': '2023-01-04',
    },
    {
        'scopus_author_id': 3,
        'title': 'Suspendisse quis magna aliquet, scelerisque mauris at, sollicitudin purus.',
        'publication_cover_date': '2023-01-05',
    },
    {
        'scopus_author_id': 3,
        'title': 'Morbi feugiat ex ut ante luctus, sed mattis turpis vehicula',
        'publication_cover_date': '2023-01-06',
    },
    {
        'scopus_author_id': 4,
        'title': 'Curabitur nec augue vel nulla elementum molestie nec eu odio',
        'publication_cover_date': '2023-01-07',
    },
    {
        'scopus_author_id': 4,
        'title': 'Fusce ut lectus fermentum, luctus mauris at, posuere arcu',
        'publication_cover_date': '2023-01-08',
    },
    {
        'scopus_author_id': 4,
        'title': 'Donec finibus nunc in lectus ullamcorper, dictum euismod neque fermentum',
        'publication_cover_date': '2023-01-09',
    },
    {
        'scopus_author_id': 4,
        'title': 'Ut et ipsum ut neque fermentum efficitur non sed felis',
        'publication_cover_date': '2023-01-10',
    },
    {
        'scopus_author_id': 5,
        'title': 'Ut tempus ante et odio tempor, et finibus mauris mattis',
        'publication_cover_date': '2023-02-01',
    },
    {
        'scopus_author_id': 5,
        'title': 'Vestibulum suscipit ipsum a massa feugiat molestie',
        'publication_cover_date': '2023-02-03',
    },
    {
        'scopus_author_id': 5,
        'title': 'Cras ullamcorper nisi vel libero volutpat, quis accumsan tellus rhoncus',
        'publication_cover_date': '2023-03-01',
    },
    {
        'scopus_author_id': 5,
        'title': 'Nunc id tellus sit amet massa sollicitudin pellentesque in sit amet velit',
        'publication_cover_date': '2023-03-02',
    },
    {
        'scopus_author_id': 5,
        'title': 'Sed id sapien convallis, ornare diam ac, egestas lacus',
        'publication_cover_date': '2023-03-03',
    },
    {
        'scopus_author_id': 6,
        'title': 'Ut viverra dolor eu quam viverra egestas',
        'publication_cover_date': '2023-01-11',
    },
    {
        'scopus_author_id': 6,
        'title': 'Aliquam rhoncus orci sed lectus iaculis, ut tempus diam iaculis',
        'publication_cover_date': '2023-01-12',
    },
    {
        'scopus_author_id': 6,
        'title': 'Donec auctor risus ut velit faucibus cursus',
        'publication_cover_date': '2023-01-13',
    },
    {
        'scopus_author_id': 6,
        'title': 'Quisque commodo sapien vel lectus commodo, eu molestie sapien blandit',
        'publication_cover_date': '2023-01-14',
    },
    {
        'scopus_author_id': 6,
        'title': 'Nullam malesuada erat quis consequat tempus',
        'publication_cover_date': '2023-01-15',
    },
    {
        'scopus_author_id': 6,
        'title': 'Integer feugiat tortor ut commodo interdum',
        'publication_cover_date': '2023-01-16',
    },
]:
    sp = Publication(
        title=p['title'],
        publication_cover_date=p['publication_cover_date'],
        subtype_id=1,
    )
    sp.sources.append(ScopusAuthor.query.get(p['scopus_author_id']))
    db.session.add(sp)

db.session.commit()

db.session.close()
