"""Add API configuration fields to users

Revision ID: e7f8g9h0i1j2
Revises: 1a2b3c4d5e6f
Create Date: 2025-10-30
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e7f8g9h0i1j2'
down_revision = '1a2b3c4d5e6f'
branch_labels = None
depends_on = None


def upgrade():
    # Add API configuration columns to users table
    op.add_column('users', sa.Column('api_provider', sa.String(), nullable=True))
    op.add_column('users', sa.Column('api_key_encrypted', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('provider_config_encrypted', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('gemini_model', sa.String(), nullable=True))
    op.add_column('users', sa.Column('vertex_model', sa.String(), nullable=True))
    op.add_column('users', sa.Column('openrouter_model', sa.String(), nullable=True))


def downgrade():
    # Remove API configuration columns from users table
    op.drop_column('users', 'openrouter_model')
    op.drop_column('users', 'vertex_model')
    op.drop_column('users', 'gemini_model')
    op.drop_column('users', 'provider_config_encrypted')
    op.drop_column('users', 'api_key_encrypted')
    op.drop_column('users', 'api_provider')
