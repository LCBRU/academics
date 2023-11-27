"""Remove publication sources

Revision ID: d927da5537d4
Revises: 6d9e040a212a
Create Date: 2023-11-27 15:32:11.696129

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'd927da5537d4'
down_revision = '6d9e040a212a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('sources__publicationses')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('sources__publicationses',
    sa.Column('source_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
    sa.Column('publication_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['publication_id'], ['publication.id'], name='sources__publicationses_ibfk_1'),
    sa.ForeignKeyConstraint(['source_id'], ['source.id'], name='sources__publicationses_ibfk_2'),
    sa.PrimaryKeyConstraint('source_id', 'publication_id'),
    mysql_collate='utf8mb4_general_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    # ### end Alembic commands ###
