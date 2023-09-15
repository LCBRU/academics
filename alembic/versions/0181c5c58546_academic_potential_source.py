"""Academic potential source

Revision ID: 0181c5c58546
Revises: d904c3c6a945
Create Date: 2023-09-15 10:55:59.727143

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0181c5c58546'
down_revision = 'd904c3c6a945'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'academic_potential_source',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('academic_id', sa.Integer, sa.ForeignKey('academic.id'), nullable=False),
        sa.Column('source_id', sa.Integer, sa.ForeignKey('source.id'), nullable=False),
        sa.Column('not_match', sa.Boolean),
    )

def downgrade():
    op.drop_table('academic_potential_source')
