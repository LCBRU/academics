"""Remove hanging source id

Revision ID: b12df0533da8
Revises: e88b88fc5409
Create Date: 2023-09-27 09:21:01.515947

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'b12df0533da8'
down_revision = 'e88b88fc5409'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('source', 'source_id')


def downgrade() -> None:
    op.add_column('source', sa.Column('source_id', mysql.VARCHAR(length=1000), nullable=True))
