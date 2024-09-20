"""Academics left brc date

Revision ID: 6ecb4ccdbd9b
Revises: 51ad920ed01c
Create Date: 2024-09-13 12:11:08.298969

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6ecb4ccdbd9b'
down_revision = '51ad920ed01c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('academic', sa.Column('left_brc_date', sa.Date(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('academic', 'left_brc_date')
    # ### end Alembic commands ###