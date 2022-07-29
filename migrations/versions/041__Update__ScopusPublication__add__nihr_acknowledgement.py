from sqlalchemy import Index, Integer, MetaData, Table, Column, Boolean, NVARCHAR, ForeignKey

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    n = Table("nihr_acknowledgement", meta, autoload=True)
    t = Table("scopus_publication", meta, autoload=True)

    nihr_acknowledgement_id = Column("nihr_acknowledgement_id", Integer, ForeignKey(n.c.id))
    nihr_acknowledgement_id.create(t)

    idx_nihr_acknowledgement_id = Index('ix__scopus_publication__nihr_acknowledgement_id', t.c.nihr_acknowledgement_id)
    idx_nihr_acknowledgement_id.create(migrate_engine)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_publication", meta, autoload=True)

    t.c.nihr_acknowledgement_id.drop()
