"""Affiliation identifier

Revision ID: 6d645f8d3315
Revises: e71a887e71e4
Create Date: 2023-10-03 17:42:38.166590

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d645f8d3315'
down_revision = 'e71a887e71e4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('affiliation', sa.Column('catalog_identifier', sa.String(length=1000), nullable=True))
    op.create_index(op.f('ix_affiliation_catalog_identifier'), 'affiliation', ['catalog_identifier'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_affiliation_catalog_identifier'), table_name='affiliation')
    op.drop_column('affiliation', 'catalog_identifier')
