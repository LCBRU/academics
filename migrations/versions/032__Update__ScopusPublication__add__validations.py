from sqlalchemy import Index, MetaData, Table, Column, Boolean

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table("scopus_publication", meta, autoload=True)

    open_access_validated = Column("open_access_validated", Boolean)
    open_access_validated.create(t)

    idx_open_access_validated = Index('ix__scopus_publication__open_access_validated', t.c.open_access_validated)
    idx_open_access_validated.create(migrate_engine)

    validation_historic = Column("validation_historic", Boolean)
    validation_historic.create(t)

    idx_validation_historic = Index('ix__scopus_publication__validation_historic', t.c.validation_historic)
    idx_validation_historic.create(migrate_engine)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_publication", meta, autoload=True)

    t.c.open_access_validated.drop()
    t.c.validation_historic.drop()
