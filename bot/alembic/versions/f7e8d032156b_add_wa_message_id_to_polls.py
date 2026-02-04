"""add wa_message_id to polls

Revision ID: f7e8d032156b
Revises:
Create Date: 2026-02-04

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f7e8d032156b"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("polls", sa.Column("wa_message_id", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("polls", "wa_message_id")
