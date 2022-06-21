from sqlalchemy import Index, Integer, MetaData, Table, Column, Boolean, NVARCHAR, ForeignKey

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    s = Table("subtype", meta, autoload=True)
    t = Table("scopus_publication", meta, autoload=True)

    subtype_id = Column("subtype_id", Integer, ForeignKey(s.c.id))
    subtype_id.create(t)

    idx = Index('ix__scopus_publication__subtype_id', t.c.subtype_id)
    idx.create(migrate_engine)

    is_open_access = Column("is_open_access", Boolean())
    is_open_access.create(t)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_publication", meta, autoload=True)

    t.c.subtype_id.drop()
    t.c.is_open_access.drop()
