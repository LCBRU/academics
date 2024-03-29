"""Remove publication sources

Revision ID: 7defdd4d102b
Revises: 9504ec8490b7
Create Date: 2023-12-29 16:45:11.604447

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '7defdd4d102b'
down_revision = '9504ec8490b7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('publications_sources')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('publications_sources',
    sa.Column('publication_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
    sa.Column('source_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
    sa.Column('ordinal', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['publication_id'], ['publication.id'], name='publications_sources_ibfk_1'),
    sa.ForeignKeyConstraint(['source_id'], ['source.id'], name='publications_sources_ibfk_2'),
    sa.PrimaryKeyConstraint('publication_id', 'source_id', 'ordinal'),
    mysql_collate='utf8mb4_general_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    # ### end Alembic commands ###
