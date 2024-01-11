"""change timestamp columns to int

Revision ID: 9b07e1756a93
Revises: 51b373966279
Create Date: 2024-01-11 01:01:36.129892

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9b07e1756a93'
down_revision = '51b373966279'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('reviews', 'created_at', type_=sa.Integer, existing_type=sa.FLOAT)
    op.alter_column('reviews', 'updated_at', type_=sa.Integer, existing_type=sa.FLOAT)


def downgrade() -> None:
    op.alter_column('reviews', 'created_at', type_=sa.FLOAT, existing_type=sa.Integer)
    op.alter_column('reviews', 'updated_at', type_=sa.FLOAT, existing_type=sa.Integer)
