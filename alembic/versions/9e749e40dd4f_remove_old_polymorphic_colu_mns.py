"""Remove old polymorphic colu,mns

Revision ID: 9e749e40dd4f
Revises: 1f33e3c78f77
Create Date: 2023-11-27 17:03:17.157198

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '9e749e40dd4f'
down_revision = '1f33e3c78f77'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # ### end Alembic commands ###
    pass

def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('source', sa.Column('source_identifier', mysql.VARCHAR(length=1000), nullable=True))
    op.add_column('source', sa.Column('type', mysql.VARCHAR(length=100), nullable=False))
    # ### end Alembic commands ###
