from sqlalchemy import Index, MetaData, Table, Column, UnicodeText

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table("scopus_publication", meta, autoload=True)

    t.c.publication.drop()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_publication", meta, autoload=True)

    publication = Column("publication", UnicodeText)
    publication.create(t)
