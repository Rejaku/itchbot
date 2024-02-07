"""add hidden field to games

Revision ID: 37db23e3b1d7
Revises: 3e243f37f420
Create Date: 2024-02-07 10:52:38.403903

"""
from alembic import op
from sqlalchemy import Column, BOOLEAN

# revision identifiers, used by Alembic.
revision = '37db23e3b1d7'
down_revision = '3e243f37f420'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('games', Column('hidden', BOOLEAN(False), default=False))


def downgrade() -> None:
    op.drop_column('games', 'hidden')
