"""PublicationSource creation

Revision ID: 1acb7dc8afee
Revises: aaa6cc1bcf2b
Create Date: 2023-11-03 12:25:50.894096

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1acb7dc8afee'
down_revision = 'aaa6cc1bcf2b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('publication_source',
    sa.Column('publication_id', sa.Integer(), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('ordinal', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['publication_id'], ['scopus_publication.id'], ),
    sa.ForeignKeyConstraint(['source_id'], ['source.id'], ),
    sa.PrimaryKeyConstraint('publication_id', 'source_id', 'ordinal')
    )


def downgrade() -> None:
    op.drop_table('publication_source')
