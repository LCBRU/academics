from sqlalchemy import MetaData, Table, Column, Integer, NVARCHAR, ForeignKey

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    u = Table("user", meta, autoload=True)
    f = Table("folder", meta, autoload=True)

    t = Table(
        "folders__shared_users",
        meta,
        Column("folder_id", Integer, ForeignKey(f.c.id), primary_key=True, index=True, nullable=False),
        Column("user_id", Integer, ForeignKey(u.c.id), primary_key=True, index=True, nullable=False),
    )
    t.create()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("folders__shared_users", meta, autoload=True)
    t.drop()
