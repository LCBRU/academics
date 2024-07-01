"""Catalog publication date in detail

Revision ID: d58da4207327
Revises: 84721ef05663
Create Date: 2024-07-01 13:35:12.910400

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd58da4207327'
down_revision = '84721ef05663'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('catalog_publication', sa.Column('publication_year', sa.Integer(), nullable=True))
    op.add_column('catalog_publication', sa.Column('publication_month', sa.Integer(), nullable=True))
    op.add_column('catalog_publication', sa.Column('publication_day', sa.Integer(), nullable=True))
    op.add_column('catalog_publication', sa.Column('publication_date_text', sa.String(length=100), nullable=True))
    op.add_column('catalog_publication', sa.Column('publication_period_start', sa.Date(), nullable=True))
    op.add_column('catalog_publication', sa.Column('publication_period_end', sa.Date(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('catalog_publication', 'publication_period_end')
    op.drop_column('catalog_publication', 'publication_period_start')
    op.drop_column('catalog_publication', 'publication_date_text')
    op.drop_column('catalog_publication', 'publication_day')
    op.drop_column('catalog_publication', 'publication_month')
    op.drop_column('catalog_publication', 'publication_year')
    # ### end Alembic commands ###