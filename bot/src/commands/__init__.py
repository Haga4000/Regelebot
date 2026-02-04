import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from commands.aide import cmd_aide
from commands.film import cmd_film
from commands.historique import cmd_historique, cmd_noter, cmd_vu
from commands.stats import cmd_stats
from commands.vote import cmd_resultats, cmd_sondage, cmd_vote

logger = logging.getLogger(__name__)

COMMANDS = {
    "/aide": cmd_aide,
    "/film": cmd_film,
    "/vu": cmd_vu,
    "/noter": cmd_noter,
    "/historique": cmd_historique,
    "/stats": cmd_stats,
    "/sondage": cmd_sondage,
    "/vote": cmd_vote,
    "/resultats": cmd_resultats,
}


async def handle_command(message: str, sender: dict, db: AsyncSession) -> Optional[str | dict]:
    parts = message.strip().split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    handler = COMMANDS.get(command)
    if not handler:
        return f"Commande inconnue : {command}\nTape /aide pour voir les commandes disponibles."

    try:
        return await handler(args=args, sender=sender, db=db)
    except Exception as e:
        logger.error("Command error %s: %s", command, e)
        return f"Erreur lors de l'execution de {command}. Reessaie !"
