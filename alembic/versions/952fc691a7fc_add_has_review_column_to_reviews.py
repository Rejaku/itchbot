"""add has_review column to reviews

Revision ID: 952fc691a7fc
Revises: 1c13100e117f
Create Date: 2024-02-14 01:37:11.172551

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '952fc691a7fc'
down_revision = '1c13100e117f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('reviews', sa.Column('has_review', sa.BOOLEAN, nullable=False, default=False))

def downgrade() -> None:
    op.drop_column('reviews', 'has_review')
