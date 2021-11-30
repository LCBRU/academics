from sqlalchemy import MetaData, Table, Column, NVARCHAR

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table("scopus_author", meta, autoload=True)

    href = Column("href", NVARCHAR(1000), default='')
    href.create(t)
    t.c.href.alter(nullable=False)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_author", meta, autoload=True)

    t.c.href.drop()
