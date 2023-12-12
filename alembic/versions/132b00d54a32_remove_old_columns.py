"""Add short numbers

Revision ID: 132b00d54a32
Revises: 9e749e40dd4f
Create Date: 2023-12-07 13:10:14.752551

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '132b00d54a32'
down_revision = '9e749e40dd4f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('source', 'source_identifier')
    op.drop_column('source', 'type')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('source', sa.Column('type', mysql.VARCHAR(length=100), nullable=False))
    op.add_column('source', sa.Column('source_identifier', mysql.VARCHAR(length=1000), nullable=True))
    # ### end Alembic commands ###