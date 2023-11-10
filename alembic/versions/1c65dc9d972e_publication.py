"""Publication

Revision ID: 1c65dc9d972e
Revises: 2adeeeb099ec
Create Date: 2023-11-10 15:01:40.153034

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1c65dc9d972e'
down_revision = '2adeeeb099ec'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('publication',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('validation_historic', sa.Boolean(), nullable=False),
    sa.Column('auto_nihr_acknowledgement_id', sa.Integer(), nullable=False),
    sa.Column('auto_nihr_funded_open_access_id', sa.Integer(), nullable=False),
    sa.Column('nihr_acknowledgement_id', sa.Integer(), nullable=False),
    sa.Column('nihr_funded_open_access_id', sa.Integer(), nullable=False),
    sa.Column('last_update_date', sa.DateTime(), nullable=False),
    sa.Column('created_date', sa.DateTime(), nullable=False),
    sa.Column('last_update_by', sa.String(length=200), nullable=False),
    sa.Column('created_by', sa.String(length=200), nullable=False),
    sa.ForeignKeyConstraint(['auto_nihr_acknowledgement_id'], ['nihr_acknowledgement.id'], ),
    sa.ForeignKeyConstraint(['auto_nihr_funded_open_access_id'], ['nihr_funded_open_access.id'], ),
    sa.ForeignKeyConstraint(['nihr_acknowledgement_id'], ['nihr_funded_open_access.id'], ),
    sa.ForeignKeyConstraint(['nihr_funded_open_access_id'], ['nihr_funded_open_access.id'], ),
    sa.PrimaryKeyConstraint('id', 'auto_nihr_acknowledgement_id', 'auto_nihr_funded_open_access_id', 'nihr_acknowledgement_id', 'nihr_funded_open_access_id')
    )


def downgrade() -> None:
    op.drop_table('publication')
