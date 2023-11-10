"""CatalogPublication

Revision ID: 4bc1d4c4f241
Revises: 1c65dc9d972e
Create Date: 2023-11-10 15:28:19.844337

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4bc1d4c4f241'
down_revision = '1c65dc9d972e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('catalog_publication',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('publication_id', sa.Integer(), nullable=False),
    sa.Column('catalog', sa.String(length=50), nullable=False),
    sa.Column('catalog_identifier', sa.String(length=500), nullable=False),
    sa.Column('doi', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=1000), nullable=False),
    sa.Column('publication_cover_date', sa.Date(), nullable=False),
    sa.Column('pubmed_id', sa.String(length=50), nullable=False),
    sa.Column('abstract', sa.UnicodeText(), nullable=False),
    sa.Column('author_list', sa.UnicodeText(), nullable=False),
    sa.Column('volume', sa.String(length=100), nullable=False),
    sa.Column('issue', sa.String(length=100), nullable=False),
    sa.Column('pages', sa.String(length=100), nullable=False),
    sa.Column('funding_text', sa.UnicodeText(), nullable=False),
    sa.Column('is_open_access', sa.Boolean(), nullable=False),
    sa.Column('cited_by_count', sa.Integer(), nullable=False),
    sa.Column('href', sa.UnicodeText(), nullable=False),
    sa.Column('journal_id', sa.Integer(), nullable=False),
    sa.Column('subtype_id', sa.Integer(), nullable=False),
    sa.Column('last_update_date', sa.DateTime(), nullable=False),
    sa.Column('created_date', sa.DateTime(), nullable=False),
    sa.Column('last_update_by', sa.String(length=200), nullable=False),
    sa.Column('created_by', sa.String(length=200), nullable=False),
    sa.ForeignKeyConstraint(['journal_id'], ['journal.id'], ),
    sa.ForeignKeyConstraint(['publication_id'], ['source.id'], ),
    sa.ForeignKeyConstraint(['subtype_id'], ['subtype.id'], ),
    sa.PrimaryKeyConstraint('id', 'publication_id', 'journal_id', 'subtype_id')
    )
    op.create_index(op.f('ix_catalog_publication_catalog'), 'catalog_publication', ['catalog'], unique=False)
    op.create_index(op.f('ix_catalog_publication_catalog_identifier'), 'catalog_publication', ['catalog_identifier'], unique=False)
    op.create_index(op.f('ix_catalog_publication_doi'), 'catalog_publication', ['doi'], unique=False)
    op.create_index(op.f('ix_catalog_publication_pubmed_id'), 'catalog_publication', ['pubmed_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_catalog_publication_pubmed_id'), table_name='catalog_publication')
    op.drop_index(op.f('ix_catalog_publication_doi'), table_name='catalog_publication')
    op.drop_index(op.f('ix_catalog_publication_catalog_identifier'), table_name='catalog_publication')
    op.drop_index(op.f('ix_catalog_publication_catalog'), table_name='catalog_publication')
    op.drop_table('catalog_publication')
