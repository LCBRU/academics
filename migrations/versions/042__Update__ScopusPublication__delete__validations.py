from sqlalchemy import Index, MetaData, Table, Column, Boolean

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_publication", meta, autoload=True)

    t.c.acknowledgement_validated.drop()


def downgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table("scopus_publication", meta, autoload=True)

    acknowledgement_validated = Column("acknowledgement_validated", Boolean)
    acknowledgement_validated.create(t)

    idx = Index('ix__scopus_publication__acknowledgement_validated', t.c.acknowledgement_validated)
    idx.create(migrate_engine)
