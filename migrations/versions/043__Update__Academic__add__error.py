from sqlalchemy import MetaData, Table, Column, NVARCHAR, BOOLEAN

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table("academic", meta, autoload=True)

    error = Column("error", BOOLEAN, default=False)
    error.create(t)
    t.c.error.alter(nullable=False)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("academic", meta, autoload=True)

    t.c.error.drop()
