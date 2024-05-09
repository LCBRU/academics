"""Remove old folder publications

Revision ID: 166739c32936
Revises: b24ac8b69166
Create Date: 2024-05-09 17:51:24.731239

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '166739c32936'
down_revision = 'b24ac8b69166'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('folders__publications')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('folders__publications',
    sa.Column('folder_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
    sa.Column('publication_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['folder_id'], ['folder.id'], name='folders__publications_ibfk_1'),
    sa.ForeignKeyConstraint(['publication_id'], ['publication.id'], name='folders__publications_ibfk_2'),
    sa.PrimaryKeyConstraint('folder_id', 'publication_id'),
    mariadb_collate='utf8mb4_general_ci',
    mariadb_default_charset='utf8mb4',
    mariadb_engine='InnoDB'
    )
    # ### end Alembic commands ###
