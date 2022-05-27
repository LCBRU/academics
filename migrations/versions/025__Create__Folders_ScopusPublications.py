from sqlalchemy import MetaData, Table, Column, Integer, NVARCHAR, ForeignKey

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    sp = Table("scopus_publication", meta, autoload=True)
    f = Table("folder", meta, autoload=True)

    t = Table(
        "folders__scopus_publications",
        meta,
        Column("folder_id", Integer, ForeignKey(f.c.id), primary_key=True, index=True, nullable=False),
        Column("scopus_publication_id", Integer, ForeignKey(sp.c.id), primary_key=True, index=True, nullable=False),
    )
    t.create()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("folders__scopus_publications", meta, autoload=True)
    t.drop()
