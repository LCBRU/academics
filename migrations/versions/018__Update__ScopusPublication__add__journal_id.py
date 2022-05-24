from sqlalchemy import Index, MetaData, Table, Column, Integer, ForeignKey

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    j = Table("journal", meta, autoload=True)
    t = Table("scopus_publication", meta, autoload=True)

    journal_id = Column("journal_id", Integer, ForeignKey(j.c.id))
    journal_id.create(t)

    idx = Index('ix__scopus_publication__journal_id', t.c.journal_id)
    idx.create(migrate_engine)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_publication", meta, autoload=True)

    t.c.journal_id.drop()
