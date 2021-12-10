from sqlalchemy import MetaData, Table, Column, Integer, ForeignKey

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    sa = Table("scopus_author", meta, autoload=True)
    sp = Table("scopus_publication", meta, autoload=True)

    t = Table(
        "scopus_author__scopus_publication",
        meta,
        Column("scopus_author_id", Integer, ForeignKey(sa.c.id), nullable=False, primary_key=True),
        Column("scopus_publication_id", Integer, ForeignKey(sp.c.id), nullable=False, primary_key=True),
    )

    t.create()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_author__scopus_publication", meta, autoload=True)
    t.drop()
