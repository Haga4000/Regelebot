from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class Member(Base):
    __tablename__ = "members"

    phone_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=True)

    ratings: Mapped[list["Rating"]] = relationship(back_populates="member")  # noqa: F821
    poll_votes: Mapped[list["PollVote"]] = relationship(back_populates="member")  # noqa: F821
