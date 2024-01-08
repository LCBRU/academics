"""Unique CatalogPublicationSource

Revision ID: f47ccf9b0cc0
Revises: 5c4ba372aa0d
Create Date: 2023-12-31 15:03:54.136487

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f47ccf9b0cc0'
down_revision = '5c4ba372aa0d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('ux__CatalogPublicationsSources__cat_pub_id__ordinal', 'catalog_publications_sources', ['catalog_publication_id', 'ordinal'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('ux__CatalogPublicationsSources__cat_pub_id__ordinal', 'catalog_publications_sources', type_='unique')
    # ### end Alembic commands ###