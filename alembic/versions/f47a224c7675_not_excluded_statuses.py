"""Not excluded statuses

Revision ID: f47a224c7675
Revises: ba7a01f22396
Create Date: 2024-12-03 17:12:49.461803

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'f47a224c7675'
down_revision = 'ba7a01f22396'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('folders__excluded_acknowledgement_statuses')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('folders__excluded_acknowledgement_statuses',
    sa.Column('folder_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
    sa.Column('nihr_acknowledgement_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['folder_id'], ['folder.id'], name='folders__excluded_acknowledgement_statuses_ibfk_1'),
    sa.ForeignKeyConstraint(['nihr_acknowledgement_id'], ['nihr_acknowledgement.id'], name='folders__excluded_acknowledgement_statuses_ibfk_2'),
    sa.PrimaryKeyConstraint('folder_id', 'nihr_acknowledgement_id'),
    mysql_collate='utf8mb4_unicode_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    # ### end Alembic commands ###
