"""Remove affiliation raw data

Revision ID: 6c555d43e526
Revises: bbcc2547b34f
Create Date: 2024-06-28 13:25:32.582393

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '6c555d43e526'
down_revision = 'bbcc2547b34f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('affiliation', 'raw_text')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('affiliation', sa.Column('raw_text', mysql.TEXT(), nullable=True))
    # ### end Alembic commands ###
