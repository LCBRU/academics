from sqlalchemy import Index, Integer, MetaData, Table, Column, Boolean, NVARCHAR, ForeignKey

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine
    t = Table("scopus_publication", meta, autoload=True)

    t.c.sponsor_id.drop()
    t.c.funding_acr_id.drop()


def downgrade(migrate_engine):
    meta.bind = migrate_engine

    s = Table("sponsor", meta, autoload=True)
    f = Table("funding_acr", meta, autoload=True)
    t = Table("scopus_publication", meta, autoload=True)

    sponsor_id = Column("sponsor_id", Integer, ForeignKey(s.c.id))
    sponsor_id.create(t)

    idx_sponsor = Index('ix__scopus_publication__sponsor_id', t.c.sponsor_id)
    idx_sponsor.create(migrate_engine)

    funding_acr_id = Column("funding_acr_id", Integer, ForeignKey(f.c.id))
    funding_acr_id.create(t)

    idx_funding_acr_id = Index('ix__scopus_publication__funding_acr_id', t.c.funding_acr_id)
    idx_funding_acr_id.create(migrate_engine)
