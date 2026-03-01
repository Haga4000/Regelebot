from sqlalchemy.ext.asyncio import AsyncSession

from services.conversation import ConversationService


async def cmd_flush(args: str, sender: dict, db: AsyncSession, group_id: str = "", **kwargs) -> str:
    if not group_id:
        return "Impossible d'effacer la memoire : groupe non identifie."
    service = ConversationService(db)
    deleted = await service.clear_recent_history(group_id)
    if deleted == 0:
        return "Aucun message recent a effacer."
    return f"Memoire recente effacee ({deleted} messages supprimes). On repart a zero !"
