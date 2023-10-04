"""Remove affiliation name from source

Revision ID: aaa6cc1bcf2b
Revises: 6296c6bc4e36
Create Date: 2023-10-04 14:43:17.940329

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'aaa6cc1bcf2b'
down_revision = '6296c6bc4e36'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('source', 'affiliation_name')


def downgrade() -> None:
    op.add_column('source', sa.Column('affiliation_name', mysql.VARCHAR(length=1000), nullable=True))
