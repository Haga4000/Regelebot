from sqlalchemy.ext.asyncio import AsyncSession

from agents.subagents.stats import StatsAgent
from config import settings


async def cmd_stats(args: str, sender: dict, db: AsyncSession, **kwargs) -> str:
    agent = StatsAgent(db, settings.TMDB_API_KEY)
    stats = await agent.get_stats()

    lines = [
        "📊 *Statistiques du club :*",
        "",
        f"🎬 Films vus : {stats['total_movies']}",
        f"⭐ Note moyenne : {stats['avg_rating']:.1f}/5",
        f"🎭 Genres preferes : {', '.join(stats['top_genres'])}",
    ]

    return "\n".join(lines)
