"""add index to games table

Revision ID: 249c814b7ac6
Revises: 021a8ab94043
Create Date: 2024-02-07 12:22:00.299888

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '249c814b7ac6'
down_revision = '021a8ab94043'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('idx_games_game_id', 'games', ['game_id'], unique=True)


def downgrade() -> None:
    op.drop_index('idx_games_game_id', 'games')
