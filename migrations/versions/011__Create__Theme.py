from sqlalchemy import MetaData, Table, Column, Integer, NVARCHAR
from lbrc_flask.security.migrations import get_audit_mixin_columns

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table(
        "theme",
        meta,
        Column("id", Integer, primary_key=True),
        Column("name", NVARCHAR(200)),
        *get_audit_mixin_columns(),
    )

    t.create()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("theme", meta, autoload=True)
    t.drop()
