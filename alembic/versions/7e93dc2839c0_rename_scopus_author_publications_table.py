"""Rename scopus_author publications table

Revision ID: 7e93dc2839c0
Revises: 6010fd959dd5
Create Date: 2023-09-27 12:06:13.582996

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '7e93dc2839c0'
down_revision = '6010fd959dd5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('sources__publications',
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('scopus_publication_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['scopus_publication_id'], ['scopus_publication.id'], ),
    sa.ForeignKeyConstraint(['source_id'], ['source.id'], ),
    sa.PrimaryKeyConstraint('source_id', 'scopus_publication_id')
    )

    conn = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(conn)

    orig = sa.Table('scopus_author__scopus_publication', meta, autoload_with=conn)
    new = sa.Table('sources__publications', meta, autoload_with=conn)

    sel = sa.select(orig.c.scopus_publication_id, orig.c.source_id)
    ins = new.insert().from_select(['scopus_publication_id', 'source_id'], sel)

    conn.execute(ins)


def downgrade() -> None:
    pass