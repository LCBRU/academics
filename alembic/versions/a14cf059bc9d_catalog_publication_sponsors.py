"""catalog publication sponsors

Revision ID: a14cf059bc9d
Revises: cde2bcd18d09
Create Date: 2023-12-30 12:27:11.560261

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a14cf059bc9d'
down_revision = 'cde2bcd18d09'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('catalog_publications_sponsors',
    sa.Column('sponsor_id', sa.Integer(), nullable=False),
    sa.Column('catalog_publication_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['catalog_publication_id'], ['catalog_publication.id'], ),
    sa.ForeignKeyConstraint(['sponsor_id'], ['sponsor.id'], ),
    sa.PrimaryKeyConstraint('sponsor_id', 'catalog_publication_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('catalog_publications_sponsors')
    # ### end Alembic commands ###
