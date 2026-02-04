from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    group_id: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    sender_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("ix_conversation_group_created", "group_id", "created_at"),
    )
