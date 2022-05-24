from sqlalchemy import MetaData, Table, Column, Integer, NVARCHAR

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table(
        "keyword",
        meta,
        Column("id", Integer, primary_key=True),
        Column("keyword", NVARCHAR(200)),
    )

    t.create()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("keyword", meta, autoload=True)
    t.drop()
