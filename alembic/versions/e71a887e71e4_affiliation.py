"""Affiliation

Revision ID: e71a887e71e4
Revises: ccfb5a852397
Create Date: 2023-10-03 17:31:17.916025

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e71a887e71e4'
down_revision = 'ccfb5a852397'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('affiliation',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('catalog', sa.String(length=100), nullable=True),
    sa.Column('name', sa.String(length=1000), nullable=True),
    sa.Column('address', sa.String(length=1000), nullable=True),
    sa.Column('country', sa.String(length=100), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_affiliation_catalog'), 'affiliation', ['catalog'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_affiliation_catalog'), table_name='affiliation')
    op.drop_table('affiliation')
