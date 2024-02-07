"""add hidden field to reviews

Revision ID: 021a8ab94043
Revises: 37db23e3b1d7
Create Date: 2024-02-07 10:53:08.071426

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, BOOLEAN

# revision identifiers, used by Alembic.
revision = '021a8ab94043'
down_revision = '37db23e3b1d7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('reviews', Column('hidden', BOOLEAN(False), default=False))


def downgrade() -> None:
    op.drop_column('reviews', 'hidden')

