"""Remove author list

Revision ID: ac2f5554a3f8
Revises: 70742d9e4f66
Create Date: 2023-12-20 16:32:09.163341

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'ac2f5554a3f8'
down_revision = '70742d9e4f66'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('catalog_publication', 'author_list')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('catalog_publication', sa.Column('author_list', mysql.TEXT(), nullable=False))
    # ### end Alembic commands ###
