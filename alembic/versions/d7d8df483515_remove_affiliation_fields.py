"""Remove affiliation fields

Revision ID: d7d8df483515
Revises: 832110f0c200
Create Date: 2023-09-27 11:04:44.175524

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'd7d8df483515'
down_revision = '832110f0c200'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('scopus_author', 'affiliation_address')
    op.drop_column('scopus_author', 'affiliation_city')
    op.drop_column('scopus_author', 'affiliation_country')
    op.drop_column('scopus_author', 'affiliation_id')


def downgrade() -> None:
    op.add_column('scopus_author', sa.Column('affiliation_id', mysql.VARCHAR(length=255), nullable=True))
    op.add_column('scopus_author', sa.Column('affiliation_country', mysql.VARCHAR(length=1000), nullable=True))
    op.add_column('scopus_author', sa.Column('affiliation_city', mysql.VARCHAR(length=1000), nullable=True))
    op.add_column('scopus_author', sa.Column('affiliation_address', mysql.VARCHAR(length=1000), nullable=True))
