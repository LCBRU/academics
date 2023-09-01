"""Move ORCID to Academic

Revision ID: 401fd7e36217
Revises: 6ee9efaf6a3f
Create Date: 2023-09-01 11:16:33.434858

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '401fd7e36217'
down_revision = '6ee9efaf6a3f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'academic',
        sa.Column('orcid', sa.String(255), nullable=True)
    )


def downgrade():
    op.drop_column('academic', 'orcid')
