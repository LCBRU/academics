"""API Key

Revision ID: 6ee9efaf6a3f
Revises: 3854904096b0
Create Date: 2023-08-30 11:51:46.586994

"""
from alembic import op
import sqlalchemy as sa
from lbrc_flask.database import GUID


# revision identifiers, used by Alembic.
revision = '6ee9efaf6a3f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'api_key',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('key', GUID, nullable=False),
        sa.Column('name', sa.String(500), nullable=False),
    )

def downgrade():
    op.drop_table('api_key')