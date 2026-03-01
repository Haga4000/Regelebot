from sqlalchemy.ext.asyncio import AsyncSession

from agents.subagents.movie import MovieAgent
from config import settings


async def cmd_film(args: str, sender: dict, db: AsyncSession, **kwargs) -> str:
    if not args.strip():
        return "Usage : /film [titre du film]"

    agent = MovieAgent(settings.TMDB_API_KEY)
    result = await agent.search(query=args.strip())

    if "error" in result:
        return f"❌ {result['error']}"

    lines = [
        f"🎬 *{result['title']}*",
    ]
    if result.get("original_title") and result["original_title"] != result["title"]:
        lines.append(f"   _{result['original_title']}_")

    lines.append(f"📅 {result.get('year', '?')} | ⏱ {result.get('runtime', '?')} min")
    lines.append(f"🎭 {', '.join(result.get('genres', []))}")
    lines.append(f"🎬 {result.get('director', 'Inconnu')}")
    lines.append(f"🌟 {result.get('vote_average', '?')}/10 ({result.get('vote_count', 0)} votes)")

    if result.get("cast"):
        lines.append(f"👥 {', '.join(result['cast'])}")

    lines.append("")
    lines.append(result.get("overview", "Pas de synopsis disponible."))

    if result.get("streaming"):
        lines.append(f"\n📺 Streaming : {', '.join(result['streaming'])}")

    if result.get("trailer"):
        lines.append(f"🎥 Trailer : {result['trailer']}")

    return "\n".join(lines)
