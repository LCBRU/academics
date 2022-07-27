from sqlalchemy import Index, Integer, MetaData, Table, Column, Boolean, NVARCHAR, ForeignKey

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    n = Table("nihr_funded_open_access", meta, autoload=True)
    t = Table("scopus_publication", meta, autoload=True)

    nihr_funded_open_access_id = Column("nihr_funded_open_access_id", Integer, ForeignKey(n.c.id))
    nihr_funded_open_access_id.create(t)

    idx_nihr_funded_open_access_id = Index('ix__scopus_publication__nihr_funded_open_access_id', t.c.nihr_funded_open_access_id)
    idx_nihr_funded_open_access_id.create(migrate_engine)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_publication", meta, autoload=True)

    t.c.nihr_funded_open_access_id.drop()
