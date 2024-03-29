"""remove publication sponsoirs and keywords

Revision ID: cfbda1579583
Revises: 434315dd1c6a
Create Date: 2023-12-30 13:07:52.842846

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'cfbda1579583'
down_revision = '434315dd1c6a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('sponsors__publications')
    op.drop_table('publication__keyword')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('publication__keyword',
    sa.Column('publication_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
    sa.Column('keyword_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['keyword_id'], ['keyword.id'], name='publication__keyword_ibfk_1'),
    sa.ForeignKeyConstraint(['publication_id'], ['publication.id'], name='publication__keyword_ibfk_2'),
    sa.PrimaryKeyConstraint('publication_id', 'keyword_id'),
    mysql_collate='utf8mb4_general_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('sponsors__publications',
    sa.Column('sponsor_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
    sa.Column('publication_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['publication_id'], ['publication.id'], name='sponsors__publications_ibfk_1'),
    sa.ForeignKeyConstraint(['sponsor_id'], ['sponsor.id'], name='sponsors__publications_ibfk_2'),
    sa.PrimaryKeyConstraint('sponsor_id', 'publication_id'),
    mysql_collate='utf8mb4_general_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    # ### end Alembic commands ###
