from sqlalchemy import MetaData, Table, Column, Integer, NVARCHAR

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table(
        "journal",
        meta,
        Column("id", Integer, primary_key=True),
        Column("name", NVARCHAR(500), index=True),
    )

    t.create()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("journal", meta, autoload=True)
    t.drop()
