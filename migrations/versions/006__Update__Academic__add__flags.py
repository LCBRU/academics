from sqlalchemy import MetaData, Table, Column, NVARCHAR, BOOLEAN

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table("academic", meta, autoload=True)

    updating = Column("updating", BOOLEAN, default=False)
    updating.create(t)
    t.c.updating.alter(nullable=False)

    initialised = Column("initialised", BOOLEAN, default=True)
    initialised.create(t)
    t.c.initialised.alter(nullable=False)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("academic", meta, autoload=True)

    t.c.updating.drop()
    t.c.initialised.drop()
