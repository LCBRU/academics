from sqlalchemy import MetaData

meta = MetaData()

def upgrade(migrate_engine):
    conn = migrate_engine.connect()

    conn.execute('''
        INSERT INTO sponsors__scopus_publications (sponsor_id, scopus_publication_id)
        SELECT DISTINCT sponsor_id, id
        FROM scopus_publication
        WHERE sponsor_id IS NOT NULL
        ;
    ''')

def downgrade(migrate_engine):
    conn = migrate_engine.connect()

    conn.execute('''
        DELETE FROM sponsors__scopus_publications;
    ''')
