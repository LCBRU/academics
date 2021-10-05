from lbrc_flask.security.migrations import create_security_tables, drop_security_tables


def upgrade(migrate_engine):
    create_security_tables(migrate_engine)

def downgrade(migrate_engine):
    drop_security_tables(migrate_engine)