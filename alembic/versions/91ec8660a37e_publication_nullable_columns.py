"""Publication Nullable columns

Revision ID: 91ec8660a37e
Revises: 4bc1d4c4f241
Create Date: 2023-11-10 16:15:40.231558

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '91ec8660a37e'
down_revision = '4bc1d4c4f241'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('publication', 'auto_nihr_acknowledgement_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=True)
    op.alter_column('publication', 'auto_nihr_funded_open_access_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=True)
    op.alter_column('publication', 'nihr_acknowledgement_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=True)
    op.alter_column('publication', 'nihr_funded_open_access_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=True)


def downgrade() -> None:
    op.alter_column('publication', 'nihr_funded_open_access_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=False)
    op.alter_column('publication', 'nihr_acknowledgement_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=False)
    op.alter_column('publication', 'auto_nihr_funded_open_access_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=False)
    op.alter_column('publication', 'auto_nihr_acknowledgement_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=False)
