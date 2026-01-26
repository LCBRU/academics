#!/usr/bin/env python3

from dotenv import load_dotenv
load_dotenv()

from random import randint, sample
from lbrc_flask.database import db
from lbrc_flask.security import init_roles, init_users
from academics.security import ROLE_EDITOR, ROLE_VALIDATOR, get_roles
from lbrc_flask.pytest.faker import LbrcFlaskFakerProvider
from tests.faker import AcademicsProvider
from faker import Faker
from academics.model.catalog import primary_catalogs

fake: Faker = Faker("en_GB")
fake.add_provider(LbrcFlaskFakerProvider)
fake.add_provider(AcademicsProvider)


from academics import create_app
from academics.model.security import User


application = create_app()
application.app_context().push()
db.drop_all()
db.create_all()
init_roles(get_roles())
init_users(admin_roles=[ROLE_VALIDATOR, ROLE_EDITOR])

# Themes
fake.theme().create_defaults()

# Sub Types
fake.subtype().create_defaults()

# Users
user = db.session.get(User, 2)
other_users = fake.user().get_list(
    save=True,
    item_count=randint(5, 10),
    email=lambda: fake.email(domain='le.ac.uk'),
)

# Folders
for u in fake.user().all_from_db():
    not_owner_users = [ou for ou in fake.user().all_from_db() if ou != u]

    fake.folder().get_list(
        save=True,
        item_count=randint(2, 5),
        owner=u,
        shared_users=set(sample(not_owner_users, randint(0, len(not_owner_users) // 2))),
    )

# Journal
fake.journal().get_list(save=True, item_count=randint(20, 40))

# Sponsor
fake.sponsor().get_list(save=True, item_count=randint(20, 40))
fake.sponsor().get(save=True, name='Leicester NIHR')
fake.sponsor().get(save=True, name='Nottingham National Institute for Health Research')
fake.sponsor().get(save=True, name='Northampton National Institute for Health and Care Research')

# Keyword
fake.keyword().get_list(save=True, item_count=randint(20, 40))
# Affiliations
fake.affiliation().get_list(save=True, item_count=randint(20, 40))
fake.affiliation().get(save=True, name='Leicester NIHR')
fake.affiliation().get(save=True, name='Nottingham National Institute for Health Research')
fake.affiliation().get(save=True, name='Northampton National Institute for Health and Care Research')

# NIHR Acknowledgements
fake.nihr_acknowledgement().create_defaults()

# Academics
fake.academic().get_list(save=True, item_count=randint(20, 40))

# Sources
for a in fake.academic().all_from_db():
    fake.source().get_list(save=True, item_count=randint(1, 5), academic=a)
# Additional Sources not linked to academics
fake.source().get_list(save=True, item_count=randint(200, 300), academic=None)

# Publications and Catalog Publications
for _ in range(randint(400, 600)):
    p = fake.publication().get(
        save=True,
        folders=set(fake.folder().choices_from_db(k=randint(0, 3))),
        auto_nihr_acknowledgement=fake.nihr_acknowledgement().choice_from_db(),
        nihr_acknowledgement=fake.nihr_acknowledgement().choice_from_db(),
        supplementary_authors=set(fake.academic().choices_from_db(k=randint(0, 3))),
    )

    for catalog in sample(primary_catalogs, randint(1, len(primary_catalogs))):
        fake.catalog_publication().get(
            save=True, 
            publication=p,
            catalog=catalog,
            keywords=set(fake.keyword().choices_from_db(k=randint(1, 5))),
            sources=set(fake.source().choices_from_db(k=randint(10, 30))),
        )

db.session.commit()
db.session.close()

from alembic.config import Config
from alembic import command
alembic_cfg = Config("alembic.ini")
command.stamp(alembic_cfg, "head")
