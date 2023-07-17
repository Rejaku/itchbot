"""add platform flags

Revision ID: 58985dc6562a
Revises: 1b92bec314ed
Create Date: 2023-07-18 00:49:01.823255

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '58985dc6562a'
down_revision = '1b92bec314ed'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('games', sa.Column('platform_windows', sa.Integer(), nullable=False, default=0))
    op.add_column('games', sa.Column('platform_linux', sa.Integer(), nullable=False, default=0))
    op.add_column('games', sa.Column('platform_mac', sa.Integer(), nullable=False, default=0))
    op.add_column('games', sa.Column('platform_android', sa.Integer(), nullable=False, default=0))
    op.add_column('games', sa.Column('platform_web', sa.Integer(), nullable=False, default=0))


def downgrade() -> None:
    op.drop_column('games', 'platform_windows')
    op.drop_column('games', 'platform_linux')
    op.drop_column('games', 'platform_mac')
    op.drop_column('games', 'platform_android')
    op.drop_column('games', 'platform_web')
