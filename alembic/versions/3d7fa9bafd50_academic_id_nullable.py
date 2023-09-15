"""Academic ID nullable

Revision ID: 3d7fa9bafd50
Revises: 4b097e42af59
Create Date: 2023-09-15 15:43:37.091497

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3d7fa9bafd50'
down_revision = '4b097e42af59'
branch_labels = None
depends_on = None


def upgrade():
	op.alter_column('source', 'academic_id', existing_type=sa.Integer, nullable=True)


def downgrade():
	op.alter_column('source', 'academic_id', existing_type=sa.Integer, nullable=False)
