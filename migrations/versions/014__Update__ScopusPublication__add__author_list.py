from sqlalchemy import MetaData, Table, Column, UnicodeText

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table("scopus_publication", meta, autoload=True)

    author_list = Column("author_list", UnicodeText)
    author_list.create(t)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_publication", meta, autoload=True)

    t.c.author_list.drop()
