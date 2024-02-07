"""add nsfw column to games

Revision ID: c13c29353fef
Revises: 72552de6f771
Create Date: 2024-02-07 22:27:26.698237

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, BOOLEAN

# revision identifiers, used by Alembic.
revision = 'c13c29353fef'
down_revision = '72552de6f771'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('games', Column('nsfw', BOOLEAN(False), default=False))


def downgrade() -> None:
    op.drop_column('games', 'nsfw')
