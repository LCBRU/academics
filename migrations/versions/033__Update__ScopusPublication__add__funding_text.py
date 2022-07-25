from sqlalchemy import MetaData, Table, Column, UnicodeText

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table("scopus_publication", meta, autoload=True)

    funding_text = Column("funding_text", UnicodeText)
    funding_text.create(t)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_publication", meta, autoload=True)

    t.c.funding_text.drop()
