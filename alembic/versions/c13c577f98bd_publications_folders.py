"""Publications folders

Revision ID: c13c577f98bd
Revises: 5553e1f2684d
Create Date: 2023-11-20 15:45:56.923313

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c13c577f98bd'
down_revision = '5553e1f2684d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('publication__keyword',
    sa.Column('publication_id', sa.Integer(), nullable=False),
    sa.Column('keyword_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['keyword_id'], ['keyword.id'], ),
    sa.ForeignKeyConstraint(['publication_id'], ['publication.id'], ),
    sa.PrimaryKeyConstraint('publication_id', 'keyword_id')
    )
    op.create_table('sponsors__publications',
    sa.Column('sponsor_id', sa.Integer(), nullable=False),
    sa.Column('publication_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['publication_id'], ['publication.id'], ),
    sa.ForeignKeyConstraint(['sponsor_id'], ['sponsor.id'], ),
    sa.PrimaryKeyConstraint('sponsor_id', 'publication_id')
    )
    op.create_table('folders__publications',
    sa.Column('folder_id', sa.Integer(), nullable=False),
    sa.Column('publication_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['folder_id'], ['folder.id'], ),
    sa.ForeignKeyConstraint(['publication_id'], ['publication.id'], ),
    sa.PrimaryKeyConstraint('folder_id', 'publication_id')
    )


def downgrade() -> None:
    op.drop_table('folders__publications')
    op.drop_table('sponsors__publications')
    op.drop_table('publication__keyword')
