"""Add audit data to raw data

Revision ID: 84721ef05663
Revises: cc3555966bfa
Create Date: 2024-07-01 10:05:51.267065

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '84721ef05663'
down_revision = 'cc3555966bfa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('raw_data', sa.Column('last_update_date', sa.DateTime(), nullable=False))
    op.add_column('raw_data', sa.Column('created_date', sa.DateTime(), nullable=False))
    op.add_column('raw_data', sa.Column('last_update_by', sa.String(length=200), nullable=False))
    op.add_column('raw_data', sa.Column('created_by', sa.String(length=200), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('raw_data', 'created_by')
    op.drop_column('raw_data', 'last_update_by')
    op.drop_column('raw_data', 'created_date')
    op.drop_column('raw_data', 'last_update_date')
    # ### end Alembic commands ###