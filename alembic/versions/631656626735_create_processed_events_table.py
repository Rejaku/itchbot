"""empty message

Revision ID: 631656626735
Revises: 6d80fffd6ae4
Create Date: 2024-12-30 03:14:01.058335

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '631656626735'
down_revision = '6d80fffd6ae4'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('last_processed_event')

    op.create_table('processed_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('game_id', sa.Integer(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    # Add index for faster lookups
    op.create_index('idx_processed_events_event_id', 'processed_events', ['event_id'])


def downgrade():
    op.drop_index('idx_processed_events_event_id')
    op.drop_table('processed_events')

    op.create_table('last_processed_event',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
