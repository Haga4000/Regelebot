import logging
from typing import Optional

import httpx

from constants.tmdb import GENRE_MAP, PROVIDER_MAP

logger = logging.getLogger(__name__)


class MovieAgent:
    def __init__(self, tmdb_api_key: str):
        self.api_key = tmdb_api_key
        self.base_url = "https://api.themoviedb.org/3"
        self.client = httpx.AsyncClient(timeout=10.0)

    async def search(self, query: str, year: Optional[int] = None) -> dict:
        params = {
            "api_key": self.api_key,
            "query": query,
            "language": "fr-FR",
        }
        if year:
            params["year"] = year

        response = await self.client.get(
            f"{self.base_url}/search/movie", params=params
        )
        results = response.json().get("results", [])

        if not results:
            return {"error": f"Aucun film trouve pour '{query}'"}

        movie_id = results[0]["id"]
        return await self._get_details(movie_id)

    async def _get_details(self, movie_id: int) -> dict:
        params = {
            "api_key": self.api_key,
            "language": "fr-FR",
            "append_to_response": "credits,videos,watch/providers",
        }

        response = await self.client.get(
            f"{self.base_url}/movie/{movie_id}", params=params
        )
        data = response.json()

        director = next(
            (
                p["name"]
                for p in data.get("credits", {}).get("crew", [])
                if p["job"] == "Director"
            ),
            "Inconnu",
        )

        cast = [a["name"] for a in data.get("credits", {}).get("cast", [])[:5]]

        trailer = next(
            (
                f"https://youtu.be/{v['key']}"
                for v in data.get("videos", {}).get("results", [])
                if v["type"] == "Trailer" and v["site"] == "YouTube"
            ),
            None,
        )

        providers = data.get("watch/providers", {}).get("results", {}).get("FR", {})
        streaming = [p["provider_name"] for p in providers.get("flatrate", [])]

        return {
            "title": data.get("title"),
            "original_title": data.get("original_title"),
            "year": data.get("release_date", "")[:4],
            "runtime": data.get("runtime"),
            "genres": [g["name"] for g in data.get("genres", [])],
            "overview": data.get("overview"),
            "vote_average": data.get("vote_average"),
            "vote_count": data.get("vote_count"),
            "director": director,
            "cast": cast,
            "trailer": trailer,
            "streaming": streaming,
            "poster": (
                f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}"
                if data.get("poster_path")
                else None
            ),
        }

    async def now_playing(self) -> dict:
        params = {
            "api_key": self.api_key,
            "language": "fr-FR",
            "region": "FR",
        }

        response = await self.client.get(
            f"{self.base_url}/movie/now_playing", params=params
        )
        results = response.json().get("results", [])

        if not results:
            return {"error": "Aucun film a l'affiche trouve"}

        movies = []
        for m in results[:10]:
            overview = m.get("overview", "")
            if len(overview) > 150:
                overview = overview[:147] + "..."
            movies.append(
                {
                    "title": m.get("title"),
                    "year": m.get("release_date", "")[:4],
                    "vote_average": m.get("vote_average"),
                    "overview": overview,
                }
            )

        return {"now_playing": movies}

    async def discover(
        self,
        genre: Optional[str] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        platform: Optional[str] = None,
        sort_by: str = "popularity.desc",
        min_rating: Optional[float] = None,
        language: Optional[str] = None,
    ) -> dict:
        params: dict = {
            "api_key": self.api_key,
            "language": "fr-FR",
            "sort_by": sort_by,
            "vote_count.gte": 50,
        }

        if genre:
            genre_id = GENRE_MAP.get(genre.lower())
            if genre_id:
                params["with_genres"] = genre_id

        if year_min:
            params["primary_release_date.gte"] = f"{year_min}-01-01"
        if year_max:
            params["primary_release_date.lte"] = f"{year_max}-12-31"

        if platform:
            provider_id = PROVIDER_MAP.get(platform.lower())
            if provider_id:
                params["with_watch_providers"] = provider_id
                params["watch_region"] = "FR"

        if min_rating is not None:
            params["vote_average.gte"] = min_rating
            params["vote_count.gte"] = 200

        if language:
            params["with_original_language"] = language

        response = await self.client.get(
            f"{self.base_url}/discover/movie", params=params
        )
        results = response.json().get("results", [])

        if not results:
            return {"error": "Aucun film trouve avec ces criteres"}

        movies = []
        for m in results[:10]:
            overview = m.get("overview", "")
            if len(overview) > 150:
                overview = overview[:147] + "..."
            movies.append(
                {
                    "title": m.get("title"),
                    "year": m.get("release_date", "")[:4],
                    "vote_average": m.get("vote_average"),
                    "overview": overview,
                }
            )

        return {"discover_results": movies}

    async def trending(self, window: str = "week") -> dict:
        if window not in ("day", "week"):
            window = "week"

        params = {
            "api_key": self.api_key,
            "language": "fr-FR",
        }

        response = await self.client.get(
            f"{self.base_url}/trending/movie/{window}", params=params
        )
        results = response.json().get("results", [])

        if not results:
            return {"error": "Aucun film tendance trouve"}

        movies = []
        for m in results[:10]:
            overview = m.get("overview", "")
            if len(overview) > 150:
                overview = overview[:147] + "..."
            movies.append(
                {
                    "title": m.get("title"),
                    "year": m.get("release_date", "")[:4],
                    "vote_average": m.get("vote_average"),
                    "overview": overview,
                }
            )

        return {"trending": movies, "window": window}
