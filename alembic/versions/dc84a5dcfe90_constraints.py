"""Constraints

Revision ID: dc84a5dcfe90
Revises: d927da5537d4
Create Date: 2023-11-27 15:43:26.645377

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dc84a5dcfe90'
down_revision = 'd927da5537d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('publication_ibfk_2', 'publication', type_='foreignkey')
    op.create_foreign_key(None, 'publication', 'nihr_acknowledgement', ['nihr_acknowledgement_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'publication', type_='foreignkey')
    op.create_foreign_key('publication_ibfk_2', 'publication', 'nihr_funded_open_access', ['nihr_acknowledgement_id'], ['id'])
    # ### end Alembic commands ###
