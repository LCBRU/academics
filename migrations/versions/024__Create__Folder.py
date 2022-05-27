from sqlalchemy import MetaData, Table, Column, Integer, NVARCHAR, ForeignKey

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    u = Table("user", meta, autoload=True)

    t = Table(
        "folder",
        meta,
        Column("id", Integer, primary_key=True),
        Column("name", NVARCHAR(500), index=True),
        Column("owner_id", Integer, ForeignKey(u.c.id), index=True, nullable=False),
    )

    t.create()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("folder", meta, autoload=True)
    t.drop()
