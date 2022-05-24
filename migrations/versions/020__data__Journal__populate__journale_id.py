from sqlalchemy import MetaData
from sqlalchemy.orm.session import sessionmaker
from academics.model import Journal, ScopusPublication


meta = MetaData()

def upgrade(migrate_engine):
    conn = migrate_engine.connect()
    Session = sessionmaker(bind=migrate_engine)
    session = Session()

    journals = {j.name: j for j in session.query(Journal).all()}

    for p in session.query(ScopusPublication).all():
        pub_name = p.publication.lower().strip()

        p.journal_id = journals[pub_name].id
        session.add(p)

    session.commit()


def downgrade(migrate_engine):
    pass
