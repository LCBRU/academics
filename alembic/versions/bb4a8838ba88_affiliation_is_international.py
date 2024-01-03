"""Affiliation is international

Revision ID: bb4a8838ba88
Revises: e7175e45043e
Create Date: 2024-01-03 16:54:59.194294

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bb4a8838ba88'
down_revision = 'e7175e45043e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('affiliation', sa.Column('international', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('affiliation', 'international')
    # ### end Alembic commands ###
