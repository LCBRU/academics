"""Add fs_uniqu thing

Revision ID: 3854904096b0
Revises: 
Create Date: 2023-05-23 12:20:14.795300

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3854904096b0'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # be sure to MODIFY this line to make nullable=True:
    op.add_column('user', sa.Column('fs_uniquifier', sa.String(length=64), nullable=True))

    # update existing rows with unique fs_uniquifier
    import uuid
    user_table = sa.Table('user', sa.MetaData(), sa.Column('id', sa.Integer, primary_key=True),
                        sa.Column('fs_uniquifier', sa.String))
    conn = op.get_bind()

    for row in conn.execute(sa.select(user_table.c.id)):
        conn.execute(user_table.update().values(fs_uniquifier=uuid.uuid4().hex).where(user_table.c.id == row[0]))

    # finally - set nullable to false
    # op.alter_column('user', 'fs_uniquifier', nullable=False)


def downgrade() -> None:
    op.drop_column('user', 'fs_uniquifier')
