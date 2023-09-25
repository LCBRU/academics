"""Academics leave BRC

Revision ID: 49560e336f30
Revises: 6b5c1463c48b
Create Date: 2023-09-25 12:16:45.739513

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '49560e336f30'
down_revision = '6b5c1463c48b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('academic', sa.Column('has_left_brc', sa.Boolean(), nullable=True))
    op.execute("UPDATE academic SET has_left_brc = false")
    op.alter_column('academic', 'has_left_brc', existing_type=sa.Boolean(), nullable=False)


def downgrade() -> None:
    op.drop_column('academic', 'has_left_brc')
