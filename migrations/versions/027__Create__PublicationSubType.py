from sqlalchemy import MetaData, Table, Column, Integer, NVARCHAR

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table(
        "subtype",
        meta,
        Column("id", Integer, primary_key=True),
        Column("code", NVARCHAR(20), index=True),
        Column("description", NVARCHAR(255)),
    )

    t.create()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("subtype", meta, autoload=True)
    t.drop()
