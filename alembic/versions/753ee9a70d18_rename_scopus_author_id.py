"""Rename scopus_author_id

Revision ID: 753ee9a70d18
Revises: 50ed13be4fe4
Create Date: 2023-09-27 11:44:37.267414

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '753ee9a70d18'
down_revision = '50ed13be4fe4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # op.add_column('scopus_author__scopus_publication', sa.Column('source_id', sa.Integer(), nullable=False))
    # op.drop_constraint('scopus_author__scopus_publication_ibfk_3', 'scopus_author__scopus_publication', type_='foreignkey')

    conn = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(conn)
    tab = sa.Table('scopus_author__scopus_publication', meta, autoload_with=conn)

    conn.execute(
        sa.update(tab).values(source_id=tab.c.scopus_author_id)
    )


def downgrade() -> None:
    conn = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(conn)
    tab = sa.Table('scopus_author__scopus_publication', meta, autoload_with=conn)

    conn.execute(
        sa.update(tab).values(scopus_author_id=tab.c.source_id)
    )

    # op.create_foreign_key('scopus_author__scopus_publication_ibfk_3', 'scopus_author__scopus_publication', 'source', ['scopus_author_id'], ['id'])
    # op.drop_column('scopus_author__scopus_publication', 'source_id')
