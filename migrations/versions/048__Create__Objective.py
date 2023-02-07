from sqlalchemy import BOOLEAN, MetaData, Table, Column, Integer, NVARCHAR, ForeignKey
from lbrc_flask.security.migrations import get_audit_mixin_columns

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    th = Table("theme", meta, autoload=True)

    t = Table(
        "objective",
        meta,
        Column("id", Integer, primary_key=True),
        Column("name", NVARCHAR(500)),
        Column("theme_id", Integer, ForeignKey(th.c.id), index=True, nullable=False),
        Column("completed", BOOLEAN),
        *get_audit_mixin_columns(),
    )

    t.create()

def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("objective", meta, autoload=True)
    t.drop()
