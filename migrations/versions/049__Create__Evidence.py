from sqlalchemy import BOOLEAN, MetaData, Table, Column, Integer, NVARCHAR, ForeignKey, UnicodeText
from lbrc_flask.security.migrations import get_audit_mixin_columns

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    o = Table("objective", meta, autoload=True)
    p = Table("scopus_publication", meta, autoload=True)

    t = Table(
        "evidence",
        meta,
        Column("id", Integer, primary_key=True),
        Column("type", NVARCHAR(100)),
        Column("notes", UnicodeText),
        Column("objective_id", Integer, ForeignKey(o.c.id), index=True, nullable=False),
        Column("scopus_publication_id", Integer, ForeignKey(p.c.id), index=True, nullable=True),
        *get_audit_mixin_columns(),
    )

    t.create()

def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("evidence", meta, autoload=True)
    t.drop()
