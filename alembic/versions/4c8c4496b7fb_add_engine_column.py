"""Add engine column

Revision ID: 4c8c4496b7fb
Revises: 5546b350b60c
Create Date: 2023-07-27 20:07:47.014023

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, String

# revision identifiers, used by Alembic.
revision = '4c8c4496b7fb'
down_revision = '5546b350b60c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('games', Column('engine', String(50)))


def downgrade() -> None:
    op.drop_column('games', 'engine')
