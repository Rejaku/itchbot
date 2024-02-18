"""Add ratings columns to game_versions

Revision ID: 3c757877ba0b
Revises: 7d0d2175e4f0
Create Date: 2024-02-18 01:03:41.646051

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3c757877ba0b'
down_revision = '7d0d2175e4f0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('game_versions', sa.Column('rating', sa.Float()))
    op.add_column('game_versions', sa.Column('rating_count', sa.Integer()))


def downgrade() -> None:
    op.drop_column('game_versions', 'rating')
    op.drop_column('game_versions', 'rating_count')
