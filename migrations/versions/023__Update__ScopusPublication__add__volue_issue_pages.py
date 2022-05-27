from sqlalchemy import Index, MetaData, Table, Column, Boolean, NVARCHAR

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table("scopus_publication", meta, autoload=True)

    volume = Column("volume", NVARCHAR(50))
    volume.create(t)
    issue = Column("issue", NVARCHAR(50))
    issue.create(t)
    pages = Column("pages", NVARCHAR(50))
    pages.create(t)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_publication", meta, autoload=True)

    t.c.volume.drop()
    t.c.issue.drop()
    t.c.pages.drop()
