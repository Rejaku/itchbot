"""Make updated_at nullable

Revision ID: a48361682c51
Revises: 01f57399b444
Create Date: 2023-01-02 02:27:57.835658

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a48361682c51'
down_revision = '01f57399b444'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('visual_novels', 'updated_at', nullable=True, existing_type=sa.FLOAT)


def downgrade() -> None:
    op.alter_column('visual_novels', 'updated_at', nullable=False, existing_type=sa.FLOAT)

