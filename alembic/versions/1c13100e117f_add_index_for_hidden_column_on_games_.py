"""add index for hidden column on games table

Revision ID: 1c13100e117f
Revises: b355156854ec
Create Date: 2024-02-10 00:10:51.747686

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1c13100e117f'
down_revision = 'b355156854ec'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('idx_games_hidden', 'games', ['hidden'])


def downgrade() -> None:
    op.drop_index('idx_games_hidden', 'games')
