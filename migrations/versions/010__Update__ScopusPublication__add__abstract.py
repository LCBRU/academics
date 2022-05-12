from sqlalchemy import MetaData, Table, Column, UnicodeText

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table("scopus_publication", meta, autoload=True)

    abstract = Column("abstract", UnicodeText)
    abstract.create(t)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("academic", meta, autoload=True)

    t.c.abstract.drop()
