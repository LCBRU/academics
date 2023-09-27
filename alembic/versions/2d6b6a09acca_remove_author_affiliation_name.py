"""Remove author affiliation name

Revision ID: 2d6b6a09acca
Revises: e9fae9d345d8
Create Date: 2023-09-27 11:12:16.491684

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '2d6b6a09acca'
down_revision = 'e9fae9d345d8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('scopus_author', 'affiliation_name')


def downgrade() -> None:
    op.add_column('scopus_author', sa.Column('affiliation_name', mysql.VARCHAR(length=1000), nullable=True))
