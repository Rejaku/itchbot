"""Add ratings and tags columns

Revision ID: 6553d5cccead
Revises: 642b63e0b68b
Create Date: 2023-01-03 01:58:36.738082

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, Float, String

# revision identifiers, used by Alembic.
revision = '6553d5cccead'
down_revision = '642b63e0b68b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('visual_novels', Column('tags', String(250)))
    op.add_column('visual_novels', Column('rating', Float()))


def downgrade() -> None:
    op.drop_column('visual_novels', 'tags')
    op.drop_column('visual_novels', 'rating')
