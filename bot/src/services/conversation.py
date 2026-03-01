from sqlalchemy import delete, select
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

    async def clear_recent_history(self, group_id: str) -> int:
        """Delete the last CONVERSATION_WINDOW_SIZE messages for a group.

        Returns the number of deleted rows.
        """
        limit = settings.CONVERSATION_WINDOW_SIZE
        # Step 1: fetch the IDs of the most recent messages
        id_stmt = (
            select(ConversationMessage.id)
            .where(ConversationMessage.group_id == group_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(limit)
        )
        rows = await self.db.execute(id_stmt)
        ids_to_delete = [row[0] for row in rows.all()]
        if not ids_to_delete:
            return 0
        # Step 2: delete by those IDs
        del_stmt = delete(ConversationMessage).where(
            ConversationMessage.id.in_(ids_to_delete)
        )
        result = await self.db.execute(del_stmt)
        await self.db.flush()
        return result.rowcount
