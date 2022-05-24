from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Integer,
    ForeignKey,
)

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    sp = Table("scopus_publication", meta, autoload=True)
    k = Table("keyword", meta, autoload=True)

    t = Table(
        "scopus_publication__keyword",
        meta,
        Column("scopus_publication_id", Integer, ForeignKey(sp.c.id), primary_key=True, index=True, nullable=False),
        Column("keyword_id", Integer, ForeignKey(k.c.id), primary_key=True, index=True, nullable=False),
    )
    t.create()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_publication__keyword", meta, autoload=True)
    t.drop()
