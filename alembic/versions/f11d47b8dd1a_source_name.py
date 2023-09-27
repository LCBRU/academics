"""Source name

Revision ID: f11d47b8dd1a
Revises: 49560e336f30
Create Date: 2023-09-27 09:04:56.129531

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'f11d47b8dd1a'
down_revision = '49560e336f30'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('source', sa.Column('first_name', sa.String(length=255), nullable=True))
    op.add_column('source', sa.Column('last_name', sa.String(length=255), nullable=True))
    op.add_column('source', sa.Column('display_name', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('source', 'display_name')
    op.drop_column('source', 'last_name')
    op.drop_column('source', 'first_name')
