"""Remove scopus_author publications table

Revision ID: ccfb5a852397
Revises: 7e93dc2839c0
Create Date: 2023-09-27 12:07:19.236442

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'ccfb5a852397'
down_revision = '7e93dc2839c0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # op.drop_table('scopus_author__scopus_publication')
    pass

def downgrade() -> None:
    pass