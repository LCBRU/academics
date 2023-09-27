"""Lets try again

Revision ID: ffd9f62b25ac
Revises: 2fc1e5b13b29
Create Date: 2023-09-27 09:57:09.710208

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ffd9f62b25ac'
down_revision = '2fc1e5b13b29'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # op.drop_column('scopus_author', 'academic_id')
    # op.drop_column('scopus_author', 'last_fetched_datetime')
    # op.drop_column('scopus_author', 'document_count')
    # op.drop_column('scopus_author', 'scopus_id')
    # op.drop_column('scopus_author', 'orcid')
    # op.drop_column('scopus_author', 'h_index')
    # op.drop_column('scopus_author', 'citation_count')
    pass

def downgrade() -> None:
    pass