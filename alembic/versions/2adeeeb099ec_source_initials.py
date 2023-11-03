"""Source initials

Revision ID: 2adeeeb099ec
Revises: 1acb7dc8afee
Create Date: 2023-11-03 16:36:04.639911

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2adeeeb099ec'
down_revision = '1acb7dc8afee'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('source', sa.Column('initials', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('source', 'initials')
