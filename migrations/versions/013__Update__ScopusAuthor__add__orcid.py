from operator import index
from sqlalchemy import ForeignKey, Integer, MetaData, Table, Column, NVARCHAR
from sqlalchemy import Index


meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table("scopus_author", meta, autoload=True)

    orcid = Column("orcid", NVARCHAR(50))
    orcid.create(t)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_author", meta, autoload=True)

    t.c.orcid.drop()
