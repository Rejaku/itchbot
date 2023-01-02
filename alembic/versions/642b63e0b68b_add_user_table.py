"""add user table

Revision ID: 642b63e0b68b
Revises: fcdeb7fb3bb0
Create Date: 2023-01-02 16:50:11.408707

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '642b63e0b68b'
down_revision = 'fcdeb7fb3bb0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('discord_id', sa.String(100), nullable=False),
        sa.Column('processed_at', sa.Integer, nullable=False),
    )


def downgrade():
    op.drop_table('users')
