from operator import index
from sqlalchemy import ForeignKey, Integer, MetaData, Table, Column
from sqlalchemy import Index


meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    th = Table("theme", meta, autoload=True)
    t = Table("academic", meta, autoload=True)

    theme_id = Column("theme_id", Integer, ForeignKey(th.c.id))
    theme_id.create(t)

    idx = Index('ix__academic__theme_id', t.c.theme_id)
    idx.create(migrate_engine)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("academic", meta, autoload=True)

    t.c.theme_id.drop()
