from sqlalchemy import MetaData, Table, Column, DateTime

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table("scopus_author", meta, autoload=True)

    last_fetched_datetime = Column("last_fetched_datetime", DateTime)
    last_fetched_datetime.create(t)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_author", meta, autoload=True)

    t.c.last_fetched_datetime.drop()
