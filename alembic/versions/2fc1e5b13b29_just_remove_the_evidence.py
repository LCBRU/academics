"""Just remove the Evidence

Revision ID: 2fc1e5b13b29
Revises: e0be8b26cab8
Create Date: 2023-09-27 09:46:53.095177

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '2fc1e5b13b29'
down_revision = 'e0be8b26cab8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table('evidence')


def downgrade() -> None:
    pass
