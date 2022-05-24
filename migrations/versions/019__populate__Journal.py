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
        if pub_name not in journals:
            j = Journal(name=pub_name)
            journals[pub_name] = j
            session.add(j)
        
        p.journal = journals[pub_name]
        session.add(p)
    session.commit()


def downgrade(migrate_engine):
    Session = sessionmaker(bind=migrate_engine)
    session = Session()

    session.query(Journal).delete()
    session.commit()
