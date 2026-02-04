import logging
from typing import Optional

import httpx
from google import genai
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.movie import Movie
from models.watchlist import Watchlist

logger = logging.getLogger(__name__)


class RecommendationAgent:
    GENRE_MAP = {
        "action": 28, "aventure": 12, "animation": 16,
        "comedie": 35, "comédie": 35, "crime": 80,
        "documentaire": 99, "drame": 18, "fantastique": 14,
        "horreur": 27, "romance": 10749, "sf": 878,
        "science-fiction": 878, "thriller": 53, "guerre": 10752,
    }

    def __init__(self, tmdb_api_key: str, db_session: AsyncSession):
        self.api_key = tmdb_api_key
        self.base_url = "https://api.themoviedb.org/3"
        self.client = httpx.AsyncClient(timeout=10.0)
        self.db = db_session
        self.genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def get(
        self,
        rec_type: str,
        reference: Optional[str] = None,
        genre: Optional[str] = None,
        mood: Optional[str] = None,
    ) -> dict:
        watched_ids = await self._get_watched_tmdb_ids()
        candidates = []

        if rec_type == "similar" and reference:
            candidates = await self._get_similar(reference)
        elif rec_type == "genre" and genre:
            genre_id = self.GENRE_MAP.get(genre.lower())
            if genre_id:
                candidates = await self._discover_by_genre(genre_id)
        elif rec_type == "mood" and mood:
            genre_ids = await self._mood_to_genres(mood)
            for gid in genre_ids[:2]:
                candidates.extend(await self._discover_by_genre(gid))

        seen: set[int] = set()
        results = []
        for movie in candidates:
            mid = movie["id"]
            if mid not in watched_ids and mid not in seen:
                seen.add(mid)
                results.append({
                    "title": movie["title"],
                    "year": movie.get("release_date", "")[:4],
                    "vote_average": movie.get("vote_average"),
                    "overview": (movie.get("overview") or "")[:200] + "...",
                })
            if len(results) >= 5:
                break

        return {
            "recommendations": results,
            "type": rec_type,
            "criteria": reference or genre or mood,
        }

    async def _get_similar(self, reference: str) -> list:
        params = {"api_key": self.api_key, "query": reference, "language": "fr-FR"}
        response = await self.client.get(
            f"{self.base_url}/search/movie", params=params
        )
        results = response.json().get("results", [])
        if not results:
            return []

        movie_id = results[0]["id"]
        params = {"api_key": self.api_key, "language": "fr-FR"}
        response = await self.client.get(
            f"{self.base_url}/movie/{movie_id}/similar", params=params
        )
        return response.json().get("results", [])

    async def _discover_by_genre(self, genre_id: int) -> list:
        params = {
            "api_key": self.api_key,
            "language": "fr-FR",
            "with_genres": genre_id,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 500,
        }
        response = await self.client.get(
            f"{self.base_url}/discover/movie", params=params
        )
        return response.json().get("results", [])

    async def _mood_to_genres(self, mood: str) -> list[int]:
        prompt = f"""Map this movie mood to TMDb genre IDs.
        Mood: "{mood}"
        Available genres: Action(28), Comedy(35), Drama(18), Horror(27),
        Romance(10749), Thriller(53), SciFi(878), Animation(16), Adventure(12)

        Return ONLY comma-separated genre IDs. Example: 35,10749"""

        try:
            response = await self.genai_client.aio.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
            )
            return [int(x.strip()) for x in response.text.split(",")]
        except (ValueError, AttributeError):
            return [35]  # Fallback: comedy

    async def _get_watched_tmdb_ids(self) -> set[int]:
        result = await self.db.execute(
            select(Movie.tmdb_id).join(Watchlist, Movie.id == Watchlist.movie_id)
        )
        return {row[0] for row in result.all()}
