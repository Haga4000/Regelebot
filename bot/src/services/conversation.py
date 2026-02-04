from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.conversation import ConversationMessage


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def store_message(
        self,
        group_id: str,
        role: str,
        content: str,
        sender_name: str | None = None,
    ) -> None:
        msg = ConversationMessage(
            group_id=group_id,
            role=role,
            content=content,
            sender_name=sender_name,
        )
        self.db.add(msg)
        await self.db.flush()

    async def get_recent_history(
        self,
        group_id: str,
        limit: int | None = None,
    ) -> list[ConversationMessage]:
        if limit is None:
            limit = settings.CONVERSATION_WINDOW_SIZE

        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.group_id == group_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rows = list(result.scalars().all())
        rows.reverse()
        return rows
