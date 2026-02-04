"""add conversation_messages table

Revision ID: a1b2c3d4e5f6
Revises: f7e8d032156b
Create Date: 2026-02-04

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f7e8d032156b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("group_id", sa.String(100), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("sender_name", sa.String(100), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_conversation_group_created",
        "conversation_messages",
        ["group_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_group_created", table_name="conversation_messages")
    op.drop_table("conversation_messages")
