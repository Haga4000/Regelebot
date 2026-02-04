import logging
from typing import Optional

import httpx

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
