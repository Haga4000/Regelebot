import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class Watchlist(Base):
    __tablename__ = "watchlist"

    movie_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("movies.id"), unique=True, nullable=False
    )
    suggested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("members.id"), nullable=True
    )
    watched_at: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)

    movie: Mapped["Movie"] = relationship(back_populates="watchlist")  # noqa: F821
    ratings: Mapped[list["Rating"]] = relationship(back_populates="watchlist_entry")  # noqa: F821
