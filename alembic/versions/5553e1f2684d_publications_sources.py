"""Publications Sources

Revision ID: 5553e1f2684d
Revises: b78e12c9306f
Create Date: 2023-11-20 15:38:24.491458

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5553e1f2684d'
down_revision = 'b78e12c9306f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('publications_sources',
    sa.Column('publication_id', sa.Integer(), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('ordinal', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['publication_id'], ['publication.id'], ),
    sa.ForeignKeyConstraint(['source_id'], ['source.id'], ),
    sa.PrimaryKeyConstraint('publication_id', 'source_id', 'ordinal')
    )
    op.create_index(op.f('ix_catalog_publication_doi'), 'catalog_publication', ['doi'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_catalog_publication_doi'), table_name='catalog_publication')
    op.drop_table('publications_sources')
