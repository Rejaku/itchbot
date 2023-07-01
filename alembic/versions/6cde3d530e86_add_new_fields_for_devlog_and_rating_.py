"""Add new fields for devlog and rating count

Revision ID: 6cde3d530e86
Revises: c9d3d0de8fe1
Create Date: 2023-07-01 06:07:14.091445

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String


# revision identifiers, used by Alembic.
revision = '6cde3d530e86'
down_revision = 'c9d3d0de8fe1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('games', Column('devlog', String(250)))
    op.add_column('games', Column('rating_count', Integer()))


def downgrade() -> None:
    op.drop_column('games', 'devlog')
    op.drop_column('games', 'rating_count')
