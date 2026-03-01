import logging
import re
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from agents.main_agent import MainAgent
from commands import handle_command
from config import settings

logger = logging.getLogger(__name__)


class MessageRouter:
    def __init__(self, main_agent: MainAgent, db: AsyncSession):
        self.agent = main_agent
        self.db = db
        names = {settings.BOT_NAME.lower(), "regelebot"}
        pattern = "|".join(re.escape(n) for n in names)
        self.bot_mention_pattern = re.compile(rf"@(?:{pattern})\s*", re.IGNORECASE)

    def should_respond(self, message: str, *, is_direct: bool = False) -> bool:
        if message.startswith("/"):
            return True
        if is_direct:
            return True
        if self.bot_mention_pattern.search(message):
            return True
        return False

    def is_command(self, message: str) -> bool:
        return message.startswith("/")

    def clean_message(self, message: str) -> str:
        return self.bot_mention_pattern.sub("", message).strip()

    async def route(
        self,
        message: str,
        sender: dict,
        conversation_history: list | None = None,
        excluded_titles: list[str] | None = None,
        *,
        is_direct: bool = False,
        group_id: str = "",
    ) -> Optional[str | dict]:
        if not self.should_respond(message, is_direct=is_direct):
            return None

        if self.is_command(message):
            return await handle_command(message, sender, self.db, group_id=group_id)

        clean_msg = self.clean_message(message)
        logger.info("Agent processing: %s from %s", clean_msg[:50], sender["name"])
        return await self.agent.process(
            clean_msg, sender["name"], conversation_history, excluded_titles
        )
