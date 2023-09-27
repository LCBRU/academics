"""Remove unneeded scopus author columns - thats them all

Revision ID: 3c8a7b186c00
Revises: ddb9d1a04010
Create Date: 2023-09-27 11:30:27.530342

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '3c8a7b186c00'
down_revision = 'ddb9d1a04010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('scopus_author', 'eid')
    op.drop_column('scopus_author', 'href')


def downgrade() -> None:
    op.add_column('scopus_author', sa.Column('href', mysql.VARCHAR(length=1000), nullable=True))
    op.add_column('scopus_author', sa.Column('eid', mysql.VARCHAR(length=1000), nullable=True))
