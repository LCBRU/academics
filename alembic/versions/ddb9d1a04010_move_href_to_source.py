"""Move href to source

Revision ID: ddb9d1a04010
Revises: 2d6b6a09acca
Create Date: 2023-09-27 11:26:32.638576

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ddb9d1a04010'
down_revision = '2d6b6a09acca'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('source', sa.Column('href', sa.String(length=1000), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('source', 'href')
    # ### end Alembic commands ###
