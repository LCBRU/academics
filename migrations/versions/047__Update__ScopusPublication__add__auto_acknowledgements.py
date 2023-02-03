from sqlalchemy import MetaData, Table, Column, Integer, ForeignKey, Index

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table("scopus_publication", meta, autoload=True)
    na = Table("nihr_acknowledgement", meta, autoload=True)
    no = Table("nihr_funded_open_access", meta, autoload=True)

    auto_nihr_acknowledgement_id = Column("auto_nihr_acknowledgement_id", Integer, ForeignKey(na.c.id))
    auto_nihr_acknowledgement_id.create(t)

    idx_auto_nihr_acknowledgement_id = Index('ix__scopus_publication__auto_nihr_acknowledgement_id', t.c.auto_nihr_acknowledgement_id)
    idx_auto_nihr_acknowledgement_id.create(migrate_engine)

    auto_nihr_funded_open_access_id = Column("auto_nihr_funded_open_access_id", Integer, ForeignKey(no.c.id))
    auto_nihr_funded_open_access_id.create(t)

    idx_nihr_funded_open_access_id = Index('ix__scopus_publication__auto_nihr_funded_open_access_id', t.c.auto_nihr_acknowledgement_id)
    idx_nihr_funded_open_access_id.create(migrate_engine)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_publication", meta, autoload=True)

    t.c.auto_nihr_acknowledgement_id.drop()
    t.c.auto_nihr_funded_open_access_id.drop()
