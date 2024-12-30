"""empty message

Revision ID: 6d80fffd6ae4
Revises: c4bc01260a22
Create Date: 2024-12-30 02:54:22.295102

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d80fffd6ae4'
down_revision = 'c4bc01260a22'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('last_processed_event',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('last_processed_event')
