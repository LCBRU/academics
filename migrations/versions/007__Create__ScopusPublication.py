from sqlalchemy import MetaData, Table, Column, Integer, NVARCHAR, UnicodeText, Boolean, Date
from lbrc_flask.security.migrations import get_audit_mixin_columns

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table(
        "scopus_publication",
        meta,
        Column("id", Integer, primary_key=True),
        Column("scopus_id", NVARCHAR(255)),
        Column("doi", NVARCHAR(255)),
        Column("title", UnicodeText),
        Column("publication", UnicodeText),
        Column("publication_cover_date", Date),
        Column("href", NVARCHAR(1000)),
        Column("deleted", Boolean),
        *get_audit_mixin_columns(),
    )

    t.create()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_publication", meta, autoload=True)
    t.drop()