from sqlalchemy import BOOLEAN, MetaData, Table, Column, Integer, NVARCHAR

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table(
        "nihr_acknowledgement",
        meta,
        Column("id", Integer, primary_key=True),
        Column("name", NVARCHAR(500)),
        Column("acknowledged", BOOLEAN),
    )

    t.create()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("nihr_acknowledgement", meta, autoload=True)
    t.drop()
