#!/usr/bin/env python3

from dotenv import load_dotenv
load_dotenv()

from random import randint, sample, choices, choice
import string
from lbrc_flask.database import db
from lbrc_flask.security import init_roles, init_users
from academics.security import ROLE_EDITOR, ROLE_VALIDATOR, get_roles
from lbrc_flask.pytest.faker import LbrcFlaskFakerProvider
from tests.faker import AcademicsProvider
from academics.model.catalog import primary_catalogs
from faker import Faker

fake: Faker = Faker("en_GB")
fake.add_provider(LbrcFlaskFakerProvider)
fake.add_provider(AcademicsProvider)


def unique_words():
    return {fake.word().title() for _ in range(randint(20, 40))}


def unique_companies():
    return {fake.company() for _ in range(randint(20, 40))}


from academics import create_app
from academics.model.academic import Academic, Affiliation, CatalogPublicationsSources, Source
from academics.model.publication import *
from academics.model.security import User
from academics.model.theme import Theme
from academics.model.folder import Folder, FolderDoi, FolderDoiUserRelevance


application = create_app()
application.app_context().push()
db.drop_all()
db.create_all()
init_roles(get_roles())
init_users(admin_roles=[ROLE_VALIDATOR, ROLE_EDITOR])

user = db.session.get(User, 2)

other_users = []

for _ in range(randint(10, 20)):
    email = fake.email(domain='le.ac.uk')
    other_users.append(fake.user().get(save=True, 
        email=email,
        password='ct*i0*t*0',
    ))

all_users = [user] + other_users

# Sub Types
fake.subtype().create_defaults()
sub_types = list(db.session.execute(select(Subtype)).scalars())

# Themes
fake.theme().create_defaults()
themes = list(db.session.execute(select(Theme)).scalars())

# Folders
for u in all_users:
    not_owner_users = [ou for ou in all_users if ou != u]

    for _ in range(randint(1, 4)):
        fake.folder().get(save=True, 
            owner=u,
            shared_users=set(sample(not_owner_users, randint(0, len(not_owner_users) // 2)))
        )

folders = list(db.session.execute(select(Folder)).scalars())

# Journal
journals = fake.journal().get_list_in_db(item_count=randint(20, 40))

# Sponsor
fake.sponsor().get_list_in_db(item_count=randint(20, 40))
fake.sponsor().get(save=True, name='Leicester NIHR')
fake.sponsor().get(save=True, name='Nottingham National Institute for Health Research')
fake.sponsor().get(save=True, name='Northampton National Institute for Health and Care Research')
sponsors = list(db.session.execute(select(Sponsor)).scalars())

# Keyword
keywords = fake.keyword().get_list_in_db(
    item_count=randint(20, 40)
)

# Affiliations
fake.affiliation().get_list_in_db(item_count=randint(20, 40))
fake.affiliation().get(save=True, name='Leicester NIHR')
fake.affiliation().get(save=True, name='Nottingham National Institute for Health Research')
fake.affiliation().get(save=True, name='Northampton National Institute for Health and Care Research')
affiliations = list(db.session.execute(select(Affiliation)).scalars())

# NIHR Acknowledgements
fake.nihr_acknowledgement().create_defaults()
acknowledgements = list(db.session.execute(select(NihrAcknowledgement)).scalars())

# Academics
academics = [
    fake.academic().get(save=True, 
        initialised=True,
        has_left_brc=(randint(1, 10) >= 9),
        create_user=(randint(1, 10) >= 9),
    )
    for _ in range(randint(20, 40))
]

# Sources
sources = []

for a in academics:
    sources.extend(
        fake.source().get_list_in_db(
            item_count=randint(1, 5),
            academic=a,
    ))

# Additional Sources not linked to academics
sources.extend(
    fake.source().get_list_in_db(
        item_count=randint(200, 300),
        academic=None,
    )
)

# Publications and Catalog Publications
for _ in range(randint(400, 600)):
    p = fake.publication().get(save=True)

    for s in sample(academics, choice([0, 0, 0, 0, 1, 2])):
        p.supplementary_authors.append(s)

    db.session.add(p)
    db.session.commit()

    # for catalog in sample(primary_catalogs(), randint(1, len(primary_catalogs()))):
    #     fake.catalog_publication().get(save=True, 
    #         publication=p,
    #         catalog=catalog,
    #     )

db.session.close()

from alembic.config import Config
from alembic import command
alembic_cfg = Config("alembic.ini")
command.stamp(alembic_cfg, "head")
