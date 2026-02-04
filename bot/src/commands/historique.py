from sqlalchemy.ext.asyncio import AsyncSession

from agents.subagents.stats import StatsAgent
from config import settings


async def cmd_vu(args: str, sender: dict, db: AsyncSession) -> str:
    if not args.strip():
        return "Usage : /vu [titre du film]"

    agent = StatsAgent(db, settings.TMDB_API_KEY)
    result = await agent.mark_watched(movie_title=args.strip())

    if "error" in result:
        return f"❌ {result['error']}"
    return f"✅ {result['message']}"


async def cmd_noter(args: str, sender: dict, db: AsyncSession) -> str:
    parts = args.rsplit(maxsplit=1)
    if len(parts) < 2:
        return "Usage : /noter [titre du film] [1-5]"

    movie_title = parts[0].strip()
    try:
        score = int(parts[1])
    except ValueError:
        return "La note doit etre un nombre entre 1 et 5."

    if not 1 <= score <= 5:
        return "La note doit etre entre 1 et 5."

    agent = StatsAgent(db, settings.TMDB_API_KEY)
    result = await agent.rate(
        movie_title=movie_title,
        score=score,
        member_name=sender["name"],
    )

    if "error" in result:
        return f"❌ {result['error']}"
    return f"⭐ {result['message']}"


async def cmd_historique(args: str, sender: dict, db: AsyncSession) -> str:
    agent = StatsAgent(db, settings.TMDB_API_KEY)
    history = await agent.get_history(limit=10)

    if not history:
        return "📽 Aucun film dans l'historique. Utilisez /vu pour en ajouter !"

    lines = ["📽 *Derniers films vus :*", ""]
    for i, movie in enumerate(history, 1):
        rating = f"{movie['avg_rating']:.1f}/5" if movie["avg_rating"] else "pas note"
        lines.append(f"{i}. {movie['title']} ({movie['year']}) — {rating}")

    return "\n".join(lines)
