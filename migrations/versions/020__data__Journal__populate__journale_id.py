from sqlalchemy import MetaData
from sqlalchemy.orm.session import sessionmaker
from academics.model import Journal, ScopusPublication


meta = MetaData()

from sqlalchemy import MetaData

meta = MetaData()

def upgrade(migrate_engine):
    conn = migrate_engine.connect()

    conn.execute('''
        UPDATE scopus_publication
        SET journal_id = (
            SELECT id
            FROM journal j
            WHERE j.name = TRIM(LOWER(scopus_publication.publication))
        )
        ;
    ''')

def downgrade(migrate_engine):
    conn = migrate_engine.connect()

    conn.execute('''
        UPDATE scopus_publication sp
        SET sp.journal_id = NULL
        ;
    ''')
