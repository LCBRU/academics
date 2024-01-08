"""Multiple themes for academics

Revision ID: 2ef47901fc08
Revises: bb4a8838ba88
Create Date: 2024-01-03 17:01:31.006986

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2ef47901fc08'
down_revision = 'bb4a8838ba88'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('academics_themes',
    sa.Column('academic_id', sa.Integer(), nullable=False),
    sa.Column('theme_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['academic_id'], ['academic.id'], ),
    sa.ForeignKeyConstraint(['theme_id'], ['theme.id'], ),
    sa.PrimaryKeyConstraint('academic_id', 'theme_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('academics_themes')
    # ### end Alembic commands ###