"""Main Catalog{ublication

Revision ID: 9dc96758a6aa
Revises: aad0ad6ecace
Create Date: 2023-11-22 11:22:05.183833

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9dc96758a6aa'
down_revision = 'aad0ad6ecace'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('catalog_publication', sa.Column('is_main', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('catalog_publication', 'is_main')
