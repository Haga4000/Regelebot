from sqlalchemy.ext.asyncio import AsyncSession

from config import settings


async def cmd_aide(args: str, sender: dict, db: AsyncSession, **kwargs) -> str:
    return (
        "Pose-moi n'importe quelle question ou lance une conversation"
        f" en taguant *@{settings.BOT_NAME}* dans le groupe !\n\n"
        "*Commandes rapides :*\n"
        "  /film [titre] — Fiche rapide d'un film\n"
        "  /vu [film] — Marquer un film comme vu\n"
        "  /noter [film] [1-5] — Noter un film\n"
        "  /historique — Derniers films vus\n"
        "  /stats — Statistiques du club\n"
        "  /sondage Question ? | Option1 | Option2 — Creer un sondage\n"
        "  /vote [numero] — Voter sur le sondage en cours\n"
        "  /resultats — Voir les resultats du sondage\n"
        "  /flush — Effacer la memoire recente du bot\n"
        "  /aide — Cette aide"
    )
