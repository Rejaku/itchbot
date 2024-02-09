"""add column user_name to reviewers

Revision ID: bce3ebe19505
Revises: c13c29353fef
Create Date: 2024-02-09 10:49:37.284279

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bce3ebe19505'
down_revision = 'c13c29353fef'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('reviewers', sa.Column('user_name', sa.String(100), nullable=False)),


def downgrade() -> None:
    op.drop_column('reviewers', 'user_name'),
