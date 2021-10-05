from sqlalchemy import MetaData, Table, Column, Integer, NVARCHAR
from lbrc_flask.security.migrations import get_audit_mixin_columns

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    t = Table(
        "academic",
        meta,
        Column("id", Integer, primary_key=True),
        Column("scopus_id", NVARCHAR(255)),
        Column("eid", NVARCHAR(255)),
        Column("first_name", NVARCHAR(500)),
        Column("last_name", NVARCHAR(500)),
        Column("affiliation_id", NVARCHAR(500)),
        Column("affiliation_name", NVARCHAR(500)),
        Column("affiliation_address", NVARCHAR(500)),
        Column("affiliation_city", NVARCHAR(500)),
        Column("affiliation_country", NVARCHAR(500)),
        Column("citation_count", Integer),
        Column("document_count", Integer),
        Column("h_index", Integer),
        *get_audit_mixin_columns(),
    )

    t.create()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("academic", meta, autoload=True)
    t.drop()