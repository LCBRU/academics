#!/usr/bin/env python3

from random import randint, sample, choices, choice
import string
from dotenv import load_dotenv
from lbrc_flask.database import db
from lbrc_flask.security import init_roles, init_users
from academics.model.academic import Academic, Affiliation, CatalogPublicationsSources, Source
from academics.model.publication import *
from academics.model.security import User
from academics.model.theme import Theme
from academics.model.folder import Folder, FolderDoi, FolderDoiUserRelevance
from academics.security import ROLE_EDITOR, ROLE_VALIDATOR, get_roles
from faker import Faker
fake = Faker()


load_dotenv()

def unique_words():
    return {fake.word().title() for _ in range(randint(20, 40))}


def unique_companies():
    return {fake.company() for _ in range(randint(20, 40))}


from academics import create_app

application = create_app()
application.app_context().push()
db.drop_all()
db.create_all()
init_roles(get_roles())
init_users(admin_roles=[ROLE_VALIDATOR, ROLE_EDITOR])

user = db.session.get(User, 2)

other_users = [User(
    email=fake.email(),
    username=''.join(fake.random_letters())
) for _ in range(randint(10, 20))]
db.session.add_all(other_users)
db.session.commit()

# Sub Types
sub_types = [Subtype(code=st, description=st) for st in ['article', 'book', 'correction']]
db.session.add_all(sub_types)
db.session.commit()

# Themes
themes = [Theme(name=w) for w in unique_words()]
db.session.add_all(themes)
db.session.commit()

# Folders
folders = [Folder(
    name=w,
    owner=user,
    shared_users=set(sample(other_users, randint(0, len(other_users) // 2)))
) for w in unique_words()]
db.session.add_all(folders)
db.session.commit()

# Journal
journals = [Journal(name=fake.bs().title(), preprint=(randint(1, 10) >= 9)) for _ in range(randint(20, 40))]
db.session.add_all(journals)
db.session.commit()

# Sponsor
sponsors = [Sponsor(name=c) for c in unique_companies()]
sponsors.append(Sponsor(name='Leicester NIHR'))
sponsors.append(Sponsor(name='Nottingham National Institute for Health Research'))
sponsors.append(Sponsor(name='Northampton National Institute for Health and Care Research'))
db.session.add_all(sponsors)
db.session.commit()

# Keyword
keywords = [Keyword(keyword=w) for w in unique_words()]
db.session.add_all(keywords)
db.session.commit()

# Affiliations
affiliations = [Affiliation(name=c, home_organisation=(randint(1, 10) >=9)) for c in unique_companies()]
affiliations.append(Affiliation(name='Leicester NIHR'))
affiliations.append(Affiliation(name='Nottingham National Institute for Health Research'))
affiliations.append(Affiliation(name='Northampton National Institute for Health and Care Research'))
db.session.add_all(affiliations)
db.session.commit()

acknowledgements = [NihrAcknowledgement(name=a['name'], acknowledged=a['acknowledged'], colour=a['colour']) for a in [
    {
        'name': 'NIHR Acknowledged',
        'acknowledged': True,
        'colour': '#F44336',
    },
    {
        'name': 'BRC Investigators Not A Primary Author',
        'acknowledged': False,
        'colour': '#3F51B5',
    },
    {
        'name': 'Need Senior Review',
        'acknowledged': False,
        'colour': '#009688',
    },
    {
        'name': 'NIHR Not Acknowledged',
        'acknowledged': False,
        'colour': '#8BC34A',
    },
    {
        'name': 'No BRC Investigator On Publication Or Not Relevant',
        'acknowledged': False,
        'colour': '#FF5722',
    },
    {
        'name': 'Unable To Check - Full Paper Not Available',
        'acknowledged': False,
        'colour': '#9C27B0',
    },
    {
        'name': 'Not to be Submitted',
        'acknowledged': False,
        'colour': '#47535E',
    },
]]

# Acknowledgement
db.session.add_all(acknowledgements)
db.session.commit()

# Academics
academics = [Academic(
    first_name=fake.first_name(),
    last_name=fake.last_name(),
    initialised=True,
    themes=sample(themes, randint(1, 3)),
    has_left_brc=(randint(1, 10) >= 9))
    for _ in range(randint(10, 20))]

db.session.add_all(academics)
db.session.commit()

# Sources
sources = []

for a in academics:
    for _ in range(randint(1,5)):
        sources.append(Source(
            academic=a,
            first_name=a.first_name,
            last_name=a.last_name,
            display_name=f'{a.first_name} {a.last_name}',
            catalog=choice([CATALOG_SCOPUS, CATALOG_OPEN_ALEX]),
            catalog_identifier=''.join(choices(string.digits, k=randint(5, 10))),
            citation_count=randint(1, 1000),
            document_count=randint(1, 1000),
            h_index=randint(1, 100),
            affiliations=sample(affiliations, randint(1, len(affiliations))),
            orcid=''.join(choices(string.ascii_uppercase + string.digits, k=randint(10, 15))),
        ))
    for _ in range(randint(5,20)):
        sources.append(Source(
            academic=None,
            first_name=a.first_name,
            last_name=a.last_name,
            display_name=f'{a.first_name} {a.last_name}',
            catalog=choice([CATALOG_SCOPUS, CATALOG_OPEN_ALEX]),
            catalog_identifier=''.join(choices(string.digits, k=randint(5, 10))),
            citation_count=randint(1, 1000),
            document_count=randint(1, 1000),
            h_index=randint(1, 100),
            affiliations=sample(affiliations, randint(1, len(affiliations))),
            orcid=''.join(choices(string.ascii_uppercase + string.digits, k=randint(10, 15))),
        ))

db.session.add_all(sources)
db.session.commit()


catalog_publications = []

for _ in range(randint(400, 600)):
    doi = f'10.{randint(4,6)}/{"".join(choices(string.ascii_lowercase, k=randint(5, 10)))}'

    p = Publication(
        doi=doi,
        nihr_acknowledgement=choice(acknowledgements + [None]),
        preprint=choice([False, False, False, True]),
        supplementary_authors=sample(academics, choice([0, 0, 0, 0, 1, 2])),
    )

    cover_date=fake.date_between(start_date='-2y', end_date='today')

    cp = CatalogPublication(
        catalog=choice([CATALOG_SCOPUS, CATALOG_OPEN_ALEX]),
        catalog_identifier=''.join(choices(string.digits, k=randint(5, 10))),
        title=fake.sentence(nb_words=randint(16, 32)).title(),
        publication_cover_date=cover_date,
        publication_period_start=cover_date,
        publication_period_end=cover_date,
        subtype=choice(sub_types),
        publication=p,
        doi=doi,
        abstract=fake.paragraph(nb_sentences=randint(10, 20)),
        volume=randint(1,12),
        issue=randint(1,30),
        pages=f'p{randint(1,100)}',
        funding_text=fake.paragraph(nb_sentences=randint(3, 10)),
        href=fake.uri(),
        journal=choice(journals),
        is_open_access=choice([True, False]),
        sponsors=set(sample(sponsors, randint(1, len(sponsors) // 4)))
    )
    cp.keywords = set(sample(keywords, randint(1, len(keywords) // 2)))

    for i, s in enumerate(sample(sources, randint(1, len(sources) // 5))):
        cp.catalog_publication_sources.append(CatalogPublicationsSources(
            catalog_publication=cp,
            source=s,
            ordinal=i,
        ))
    
    for f in sample(folders, randint(0, len(folders) // 4)):
        db.session.add(FolderDoi(folder=f, doi=p.doi))

    catalog_publications.append(cp)

db.session.add_all(catalog_publications)
db.session.commit()

for p in db.session.execute(select(Publication)).scalars():
    p.set_vancouver()
    db.session.add(p)
db.session.commit()

other_users = list(db.session.execute(select(User).where(User.id > 2)).scalars())

for p in db.session.execute(select(Publication)).scalars():
    for f in p.folder_dois:
        for u in sample(other_users, randint(0, len(other_users))):
            db.session.add(FolderDoiUserRelevance(
                folder_doi_id=f.id,
                user=u,
                relevant=choice([True, False]),
            ))
db.session.commit()

db.session.close()

from alembic.config import Config
from alembic import command
alembic_cfg = Config("alembic.ini")
command.stamp(alembic_cfg, "head")
