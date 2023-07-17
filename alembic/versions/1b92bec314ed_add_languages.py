"""add languages

Revision ID: 1b92bec314ed
Revises: 5a9b7805d91a
Create Date: 2023-07-18 00:14:08.593123

"""
from alembic import op
from sqlalchemy import Column, String

# revision identifiers, used by Alembic.
revision = '1b92bec314ed'
down_revision = '5a9b7805d91a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('games', Column('languages', String(250)))


def downgrade() -> None:
    op.drop_column('games', 'languages')
