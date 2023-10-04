"""Affiliation linked to source

Revision ID: 6296c6bc4e36
Revises: 6d645f8d3315
Create Date: 2023-10-04 14:12:58.038776

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6296c6bc4e36'
down_revision = '6d645f8d3315'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('source', sa.Column('affiliation_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'source', 'affiliation', ['affiliation_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint(None, 'source', type_='foreignkey')
    op.drop_column('source', 'affiliation_id')
