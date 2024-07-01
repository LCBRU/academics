"""Save Raw text for institution

Revision ID: bb1c87fa8a83
Revises: 54201a556dff
Create Date: 2024-06-28 11:18:27.608360

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bb1c87fa8a83'
down_revision = '54201a556dff'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('institution', sa.Column('raw_text', sa.UnicodeText(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('institution', 'raw_text')
    # ### end Alembic commands ###