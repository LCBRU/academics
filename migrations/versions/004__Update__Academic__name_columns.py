from sqlalchemy import MetaData, Table, Column, NVARCHAR

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table("academic", meta, autoload=True)

    first_name = Column("first_name", NVARCHAR(500), default='')
    first_name.create(t)
    t.c.first_name.alter(nullable=False)

    last_name = Column("last_name", NVARCHAR(500), default='')
    last_name.create(t)
    t.c.last_name.alter(nullable=False)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("academic", meta, autoload=True)

    t.c.first_name.drop()
    t.c.last_name.drop()
