from sqlalchemy import Boolean, Index, MetaData, Table, Column

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_publication", meta, autoload=True)

    t.c.open_access_validated.drop()

def downgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table("scopus_publication", meta, autoload=True)

    open_access_validated = Column("open_access_validated", Boolean)
    open_access_validated.create(t)

    idx_open_access_validated = Index('ix__scopus_publication__open_access_validated', t.c.open_access_validated)
    idx_open_access_validated.create(migrate_engine)
