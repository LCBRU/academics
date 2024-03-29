"""Refresh sources

Revision ID: 1b18bcb8525a
Revises: 3a3dea597fae
Create Date: 2023-12-21 09:51:31.372623

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1b18bcb8525a'
down_revision = '3a3dea597fae'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('source', sa.Column('refresh_full_details', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('source', 'refresh_full_details')
    # ### end Alembic commands ###
