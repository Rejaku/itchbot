"""Add project status column

Revision ID: 5a9b7805d91a
Revises: 1edd70031902
Create Date: 2023-07-01 17:58:15.539037

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, String

# revision identifiers, used by Alembic.
revision = '5a9b7805d91a'
down_revision = '1edd70031902'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('games', Column('status', String(50)))


def downgrade() -> None:
    op.drop_column('games', 'status')
