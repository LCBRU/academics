"""Another null column

Revision ID: 6d9e040a212a
Revises: 52b8e5c4c768
Create Date: 2023-11-24 18:09:12.623311

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '6d9e040a212a'
down_revision = '52b8e5c4c768'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('catalog_publication', 'pubmed_id',
               existing_type=mysql.VARCHAR(length=50),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('catalog_publication', 'pubmed_id',
               existing_type=mysql.VARCHAR(length=50),
               nullable=False)
    # ### end Alembic commands ###
