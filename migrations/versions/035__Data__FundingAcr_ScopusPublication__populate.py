from sqlalchemy import MetaData

meta = MetaData()

def upgrade(migrate_engine):
    conn = migrate_engine.connect()

    conn.execute('''
        INSERT INTO funding_acr__scopus_publications (funding_acr_id, scopus_publication_id)
        SELECT DISTINCT funding_acr_id, id
        FROM scopus_publication
        ;
    ''')

def downgrade(migrate_engine):
    conn = migrate_engine.connect()

    conn.execute('''
        DELETE FROM funding_acr__scopus_publications;
    ''')
