"""Affilate to source

Revision ID: e9fae9d345d8
Revises: d7d8df483515
Create Date: 2023-09-27 11:08:14.150390

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e9fae9d345d8'
down_revision = 'd7d8df483515'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('source', sa.Column('affiliation_name', sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column('source', 'affiliation_name')
