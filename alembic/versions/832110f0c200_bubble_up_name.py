"""Bubble up name

Revision ID: 832110f0c200
Revises: ffd9f62b25ac
Create Date: 2023-09-27 10:44:59.422145

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '832110f0c200'
down_revision = 'ffd9f62b25ac'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('scopus_author', 'last_name')
    op.drop_column('scopus_author', 'first_name')


def downgrade() -> None:
    op.add_column('scopus_author', sa.Column('first_name', mysql.VARCHAR(length=255), nullable=True))
    op.add_column('scopus_author', sa.Column('last_name', mysql.VARCHAR(length=255), nullable=True))
