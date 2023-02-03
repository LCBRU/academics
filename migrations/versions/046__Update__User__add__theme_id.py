from sqlalchemy import MetaData, Table, Column, Integer, ForeignKey, Index

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table("user", meta, autoload=True)
    th = Table("theme", meta, autoload=True)

    theme_id = Column("theme_id", Integer, ForeignKey(th.c.id))
    theme_id.create(t)

    idx_theme_id = Index('ix__user__theme_id', t.c.theme_id)
    idx_theme_id.create(migrate_engine)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("user", meta, autoload=True)

    t.c.theme_id.drop()
