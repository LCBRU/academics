"""Add source

Revision ID: d904c3c6a945
Revises: 401fd7e36217
Create Date: 2023-09-12 16:00:36.040320

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd904c3c6a945'
down_revision = '401fd7e36217'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'source',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('type', sa.String(100), nullable=False),
        sa.Column('academic_id', sa.Integer, sa.ForeignKey('academic.id'), nullable=False),
        sa.Column('source_id', sa.Unicode(1000)),
        sa.Column('orcid', sa.Unicode(255)),
        sa.Column('citation_count', sa.Unicode(1000)),
        sa.Column('document_count', sa.Unicode(1000)),
        sa.Column('h_index', sa.Unicode(1000)),
        sa.Column('last_fetched_datetime', sa.DateTime),
        sa.Column('error', sa.Boolean),
    )

def downgrade():
    op.drop_table('source')
