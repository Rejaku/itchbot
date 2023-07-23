"""Add stats columns for wordcount and choices

Revision ID: 5546b350b60c
Revises: 58985dc6562a
Create Date: 2023-07-23 23:58:35.258388

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, Integer

# revision identifiers, used by Alembic.
revision = '5546b350b60c'
down_revision = '58985dc6562a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('games', Column('stats_blocks', Integer(), nullable=False, default=0))
    op.add_column('games', Column('stats_menus', Integer(), nullable=False, default=0))
    op.add_column('games', Column('stats_options', Integer(), nullable=False, default=0))
    op.add_column('games', Column('stats_words', Integer(), nullable=False, default=0))


def downgrade() -> None:
    op.drop_column('games', 'stats_blocks')
    op.drop_column('games', 'stats_menus')
    op.drop_column('games', 'stats_options')
    op.drop_column('games', 'stats_words')
