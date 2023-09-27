"""Remove what

Revision ID: e0be8b26cab8
Revises: b12df0533da8
Create Date: 2023-09-27 09:21:45.914287

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'e0be8b26cab8'
down_revision = 'b12df0533da8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # op.drop_constraint('scopus_author_ibfk_1', 'scopus_author', type_='foreignkey')
    # op.create_foreign_key(None, 'scopus_author', 'source', ['id'], ['id'])
    # op.drop_column('scopus_author', 'created_by')
    # op.drop_column('scopus_author', 'academic_id')
    # op.drop_column('scopus_author', 'created_date')
    # op.drop_column('scopus_author', 'last_fetched_datetime')
    # op.drop_column('scopus_author', 'document_count')
    # op.drop_column('scopus_author', 'error')
    # op.drop_column('scopus_author', 'scopus_id')
    # op.drop_column('scopus_author', 'orcid')
    # op.drop_column('scopus_author', 'last_update_by')
    # op.drop_column('scopus_author', 'last_update_date')
    # op.drop_column('scopus_author', 'h_index')
    # op.drop_column('scopus_author', 'citation_count')
    # op.drop_constraint('scopus_author__scopus_publication_ibfk_1', 'scopus_author__scopus_publication', type_='foreignkey')
    # op.create_foreign_key(None, 'scopus_author__scopus_publication', 'source', ['scopus_author_id'], ['id'])
    pass

def downgrade() -> None:
    # op.drop_constraint('scopus_author__scopus_publication_ibfk_3', 'scopus_author__scopus_publication', type_='foreignkey')
    # op.create_foreign_key('scopus_author__scopus_publication_ibfk_1', 'scopus_author__scopus_publication', 'scopus_author', ['scopus_author_id'], ['id'])
    # op.add_column('scopus_author', sa.Column('citation_count', mysql.VARCHAR(length=1000), nullable=True))
    # op.add_column('scopus_author', sa.Column('h_index', mysql.VARCHAR(length=100), nullable=True))
    # op.add_column('scopus_author', sa.Column('last_update_date', mysql.DATETIME(), nullable=False))
    # op.add_column('scopus_author', sa.Column('last_update_by', mysql.VARCHAR(length=200), nullable=False))
    # op.add_column('scopus_author', sa.Column('orcid', mysql.VARCHAR(length=255), nullable=True))
    # op.add_column('scopus_author', sa.Column('scopus_id', mysql.VARCHAR(length=1000), nullable=True))
    # op.add_column('scopus_author', sa.Column('error', mysql.TINYINT(display_width=1), autoincrement=False, nullable=True))
    # op.add_column('scopus_author', sa.Column('document_count', mysql.VARCHAR(length=1000), nullable=True))
    # op.add_column('scopus_author', sa.Column('last_fetched_datetime', mysql.DATETIME(), nullable=True))
    # op.add_column('scopus_author', sa.Column('created_date', mysql.DATETIME(), nullable=False))
    # op.add_column('scopus_author', sa.Column('academic_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True))
    # op.add_column('scopus_author', sa.Column('created_by', mysql.VARCHAR(length=200), nullable=False))
    # op.create_foreign_key('scopus_author_ibfk_1', 'scopus_author', 'academic', ['academic_id'], ['id'])
    pass