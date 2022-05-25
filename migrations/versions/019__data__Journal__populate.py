from sqlalchemy import MetaData

meta = MetaData()

def upgrade(migrate_engine):
    conn = migrate_engine.connect()

    conn.execute('''
        INSERT INTO journal (name)
        SELECT DISTINCT TRIM(LOWER(publication))
        FROM scopus_publication
        ;
    ''')

def downgrade(migrate_engine):
    conn = migrate_engine.connect()

    conn.execute('''
        DELETE FROM journal;
        ;
    ''')
