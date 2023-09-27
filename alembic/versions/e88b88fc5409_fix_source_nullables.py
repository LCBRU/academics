"""Fix source nullables

Revision ID: e88b88fc5409
Revises: f11d47b8dd1a
Create Date: 2023-09-27 09:16:40.465247

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'e88b88fc5409'
down_revision = 'f11d47b8dd1a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('source', 'last_update_date',
               existing_type=mysql.DATETIME(),
               nullable=False)
    op.alter_column('source', 'created_date',
               existing_type=mysql.DATETIME(),
               nullable=False)
    op.alter_column('source', 'last_update_by',
               existing_type=mysql.VARCHAR(length=200),
               nullable=False)
    op.alter_column('source', 'created_by',
               existing_type=mysql.VARCHAR(length=200),
               nullable=False)


def downgrade() -> None:
    op.alter_column('source', 'created_by',
               existing_type=mysql.VARCHAR(length=200),
               nullable=True)
    op.alter_column('source', 'last_update_by',
               existing_type=mysql.VARCHAR(length=200),
               nullable=True)
    op.alter_column('source', 'created_date',
               existing_type=mysql.DATETIME(),
               nullable=True)
    op.alter_column('source', 'last_update_date',
               existing_type=mysql.DATETIME(),
               nullable=True)
