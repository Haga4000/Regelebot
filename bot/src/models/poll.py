import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class Poll(Base):
    __tablename__ = "polls"

    question: Mapped[str] = mapped_column(String(500), nullable=False)
    options: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("members.id"), nullable=True
    )
    closes_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    wa_message_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    votes: Mapped[list["PollVote"]] = relationship(back_populates="poll")


class PollVote(Base):
    __tablename__ = "poll_votes"
    __table_args__ = (
        UniqueConstraint("poll_id", "member_id", name="uq_poll_vote_member"),
    )

    poll_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("polls.id"), nullable=False
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("members.id"), nullable=False
    )
    option_id: Mapped[str] = mapped_column(String(50), nullable=False)

    poll: Mapped["Poll"] = relationship(back_populates="votes")
    member: Mapped["Member"] = relationship(back_populates="poll_votes")
