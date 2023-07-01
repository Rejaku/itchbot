"""Increased length of name field

Revision ID: 1edd70031902
Revises: 6cde3d530e86
Create Date: 2023-07-01 07:30:31.772300

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1edd70031902'
down_revision = '6cde3d530e86'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('games', 'name', existing_type=sa.VARCHAR(length=50), type_=sa.VARCHAR(length=200),
                    existing_nullable=False)


def downgrade() -> None:
    op.alter_column('games', 'name', existing_type=sa.VARCHAR(length=200), type_=sa.VARCHAR(length=50),
                    existing_nullable=False)
