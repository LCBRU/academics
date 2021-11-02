from sqlalchemy import MetaData, Table, Column, Integer, NVARCHAR
from lbrc_flask.security.migrations import get_audit_mixin_columns

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table(
        "academic",
        meta,
        Column("id", Integer, primary_key=True),
        *get_audit_mixin_columns(),
    )

    t.create()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("academic", meta, autoload=True)
    t.drop()