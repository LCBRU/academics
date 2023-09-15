"""Create source identifier

Revision ID: 4b097e42af59
Revises: 0181c5c58546
Create Date: 2023-09-15 10:59:54.852688

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4b097e42af59'
down_revision = '0181c5c58546'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('source', sa.Column('source_identifier', sa.Unicode(1000)))

    conn = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(conn)
    source = sa.Table('source', meta, autoload_with=conn)

    results = conn.execute(sa.select(source.c.id, source.c.source_id)).all()
    
    for id, source_id in results:
        ins = (
            sa.update(source).
            where(source.c.id == id).
            values(source_identifier=source_id)
        )
        conn.execute(ins)


def downgrade():
    op.drop_column('source', 'source_identifier')
