"""add telegram_id to admins

Revision ID: 57bae64b5d08
Revises: 9d7e8a99950d
Create Date: 2026-09-20 16:19:49.517198

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '57bae64b5d08'
down_revision: Union[str, Sequence[str], None] = '9d7e8a99950d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('admins', sa.Column('telegram_id', sa.BigInteger(), nullable=True))
    op.create_index(op.f('ix_admins_telegram_id'), 'admins', ['telegram_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_admins_telegram_id'), table_name='admins')
    op.drop_column('admins', 'telegram_id')
