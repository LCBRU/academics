"""Now remove the column

Revision ID: 6010fd959dd5
Revises: 753ee9a70d18
Create Date: 2023-09-27 11:59:28.122423

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '6010fd959dd5'
down_revision = '753ee9a70d18'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # op.drop_column('scopus_author__scopus_publication', 'scopus_author_id')
    pass


def downgrade() -> None:
    # op.add_column('scopus_author__scopus_publication', sa.Column('scopus_author_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False))
    pass
