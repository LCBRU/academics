"""Soft delete for folderdoi

Revision ID: f45f84d6ee74
Revises: 7113b325494f
Create Date: 2024-11-15 15:05:56.154251

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f45f84d6ee74'
down_revision = '7113b325494f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('folder_doi', sa.Column('deleted', sa.Boolean(), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('folder_doi', 'deleted')
    # ### end Alembic commands ###
