"""change timestamp fields to int

Revision ID: fcdeb7fb3bb0
Revises: a48361682c51
Create Date: 2023-01-02 16:47:06.341949

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fcdeb7fb3bb0'
down_revision = 'a48361682c51'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('visual_novels', 'created_at', existing_type=sa.FLOAT, type_=sa.Integer)
    op.alter_column('visual_novels', 'updated_at', existing_type=sa.FLOAT, type_=sa.Integer)


def downgrade() -> None:
    op.alter_column('visual_novels', 'created_at', existing_type=sa.Integer, type_=sa.FLOAT)
    op.alter_column('visual_novels', 'updated_at', existing_type=sa.Integer, type_=sa.FLOAT)
