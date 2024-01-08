"""Unicode title

Revision ID: 1e24ef573965
Revises: 2ef47901fc08
Create Date: 2024-01-08 15:39:06.180658

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = '1e24ef573965'
down_revision = '2ef47901fc08'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('keyword', 'keyword', existing_type=mysql.VARCHAR(length=1000), type_=mysql.NVARCHAR(length=1000))


def downgrade() -> None:
    op.alter_column('keyword', 'keyword', existing_type=mysql.NVARCHAR(length=1000), type_=mysql.VARCHAR(length=1000))
