"""Remove scopus author table

Revision ID: 50ed13be4fe4
Revises: 3c8a7b186c00
Create Date: 2023-09-27 11:36:56.601075

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '50ed13be4fe4'
down_revision = '3c8a7b186c00'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table('scopus_author')


def downgrade() -> None:
    op.create_table('scopus_author',
    sa.Column('id', mysql.INTEGER(display_width=11), autoincrement=True, nullable=False),
    sa.ForeignKeyConstraint(['id'], ['source.id'], name='scopus_author_ibfk_1'),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_general_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
