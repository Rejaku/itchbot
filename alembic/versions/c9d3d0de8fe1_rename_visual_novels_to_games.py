"""Rename visual_novels to games

Revision ID: c9d3d0de8fe1
Revises: 6553d5cccead
Create Date: 2023-01-03 02:01:42.080001

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c9d3d0de8fe1'
down_revision = '6553d5cccead'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table('visual_novels', 'games')


def downgrade() -> None:
    op.rename_table('games', 'visual_novels')
