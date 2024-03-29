"""Vancouver

Revision ID: 3a3dea597fae
Revises: 6cd98255a37d
Create Date: 2023-12-20 17:41:08.099638

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3a3dea597fae'
down_revision = '6cd98255a37d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('publication', sa.Column('vancouver', sa.UnicodeText(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('publication', 'vancouver')
    # ### end Alembic commands ###
