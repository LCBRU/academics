"""academic_potential_source audit fields

Revision ID: 6b5c1463c48b
Revises: 3d7fa9bafd50
Create Date: 2023-09-18 13:15:28.156378

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6b5c1463c48b'
down_revision = '3d7fa9bafd50'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('academic_potential_source', sa.Column('last_update_date', sa.DateTime, nullable=False))
    op.add_column('academic_potential_source', sa.Column('last_update_by', sa.String(500), nullable=False))
    op.add_column('academic_potential_source', sa.Column('created_date', sa.DateTime, nullable=False))
    op.add_column('academic_potential_source', sa.Column('created_by', sa.String(500), nullable=False))


def downgrade() -> None:
    op.drop_column('academic_potential_source', 'last_update_date')
    op.drop_column('academic_potential_source', 'last_update_by')
    op.drop_column('academic_potential_source', 'created_date')
    op.drop_column('academic_potential_source', 'created_by')
