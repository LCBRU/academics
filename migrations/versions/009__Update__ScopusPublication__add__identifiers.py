from sqlalchemy import MetaData, Table, Column, NVARCHAR

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table("scopus_publication", meta, autoload=True)

    pubmed_id = Column("pubmed_id", NVARCHAR(255), default=False)
    pubmed_id.create(t)

    pii = Column("pii", NVARCHAR(255), default=True)
    pii.create(t)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_publication", meta, autoload=True)

    t.c.pubmed_id.drop()
    t.c.pii.drop()
