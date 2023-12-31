"""Unique academic poterntial soue

Revision ID: aece9b9dfc61
Revises: 011c30aac055
Create Date: 2023-12-31 14:56:13.330119

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aece9b9dfc61'
down_revision = '011c30aac055'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('ux__AcademicPotentialSource__academic_id__source_id', 'academic_potential_source', ['academic_id', 'source_id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('ux__AcademicPotentialSource__academic_id__source_id', 'academic_potential_source', type_='unique')
    # ### end Alembic commands ###
