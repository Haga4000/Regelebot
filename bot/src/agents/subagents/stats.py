import logging

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.member import Member
from models.movie import Movie
from models.rating import Rating
from models.watchlist import Watchlist

logger = logging.getLogger(__name__)


class StatsAgent:
    def __init__(self, db_session: AsyncSession, tmdb_api_key: str):
        self.db = db_session
        self.api_key = tmdb_api_key
        self.base_url = "https://api.themoviedb.org/3"
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_history(self, limit: int = 10) -> list[dict]:
        query = (
            select(
                Movie.title,
                Movie.year,
                Watchlist.watched_at,
                Movie.tmdb_id,
                func.avg(Rating.score).label("avg_rating"),
            )
            .join(Watchlist, Movie.id == Watchlist.movie_id)
            .outerjoin(Rating, Watchlist.id == Rating.watchlist_id)
            .group_by(Movie.id, Watchlist.id)
            .order_by(Watchlist.watched_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "title": title,
                "year": year,
                "watched_at": watched_at.isoformat(),
                "avg_rating": round(float(avg_rating), 1) if avg_rating else None,
                "tmdb_id": tmdb_id,
            }
            for title, year, watched_at, tmdb_id, avg_rating in rows
        ]

    async def get_stats(self) -> dict:
        total = await self.db.scalar(select(func.count(Watchlist.id)))
        avg_rating = await self.db.scalar(select(func.avg(Rating.score)))

        # Top genres from movies metadata
        movies_result = await self.db.execute(
            select(Movie.genres)
            .join(Watchlist, Movie.id == Watchlist.movie_id)
            .where(Movie.genres.isnot(None))
        )
        genre_count: dict[str, int] = {}
        for (genres,) in movies_result.all():
            if isinstance(genres, list):
                for g in genres:
                    genre_count[g] = genre_count.get(g, 0) + 1
        top_genres = sorted(genre_count, key=genre_count.get, reverse=True)[:5]

        return {
            "total_movies": total or 0,
            "avg_rating": round(float(avg_rating), 1) if avg_rating else 0.0,
            "top_genres": top_genres if top_genres else ["Aucun genre enregistre"],
        }

    async def mark_watched(self, movie_title: str) -> dict:
        # Search TMDb to get movie info
        params = {
            "api_key": self.api_key,
            "query": movie_title,
            "language": "fr-FR",
        }
        response = await self.client.get(
            f"{self.base_url}/search/movie", params=params
        )
        results = response.json().get("results", [])

        if not results:
            return {"error": f"Film '{movie_title}' non trouve sur TMDb"}

        tmdb_movie = results[0]
        tmdb_id = tmdb_movie["id"]

        # Check if movie exists in DB
        movie = await self.db.scalar(select(Movie).where(Movie.tmdb_id == tmdb_id))
        if not movie:
            genres = [g["name"] for g in tmdb_movie.get("genre_ids", [])] if tmdb_movie.get("genre_ids") else []
            # Fetch full details for genre names
            detail_resp = await self.client.get(
                f"{self.base_url}/movie/{tmdb_id}",
                params={"api_key": self.api_key, "language": "fr-FR"},
            )
            detail_data = detail_resp.json()
            genres = [g["name"] for g in detail_data.get("genres", [])]

            movie = Movie(
                tmdb_id=tmdb_id,
                title=tmdb_movie.get("title", movie_title),
                original_title=tmdb_movie.get("original_title"),
                year=int(tmdb_movie.get("release_date", "0000")[:4]) or None,
                genres=genres,
            )
            self.db.add(movie)
            await self.db.flush()

        # Check if already in watchlist
        existing = await self.db.scalar(
            select(Watchlist).where(Watchlist.movie_id == movie.id)
        )
        if existing:
            return {"success": True, "message": f"'{movie.title}' etait deja dans l'historique"}

        watchlist_entry = Watchlist(movie_id=movie.id)
        self.db.add(watchlist_entry)
        await self.db.flush()

        return {"success": True, "message": f"'{movie.title}' marque comme vu !"}

    async def rate(self, movie_title: str, score: int, member_name: str) -> dict:
        if not 1 <= score <= 5:
            return {"error": "La note doit etre entre 1 et 5"}

        # Find movie
        movie = await self.db.scalar(
            select(Movie).where(Movie.title.ilike(f"%{movie_title}%"))
        )
        if not movie:
            return {"error": f"Film '{movie_title}' non trouve. Utilisez /vu d'abord."}

        # Find watchlist entry
        watchlist_entry = await self.db.scalar(
            select(Watchlist).where(Watchlist.movie_id == movie.id)
        )
        if not watchlist_entry:
            return {"error": f"'{movie.title}' n'est pas dans l'historique du club"}

        # Find or create member
        member = await self.db.scalar(
            select(Member).where(Member.display_name == member_name)
        )
        if not member:
            member = Member(phone_hash=member_name.lower().replace(" ", "_"), display_name=member_name)
            self.db.add(member)
            await self.db.flush()

        # Check if already rated
        existing = await self.db.scalar(
            select(Rating).where(
                Rating.watchlist_id == watchlist_entry.id,
                Rating.member_id == member.id,
            )
        )
        if existing:
            existing.score = score
            await self.db.flush()
            return {"success": True, "message": f"Note mise a jour : {member_name} a donne {score}/5 a '{movie.title}'"}

        rating = Rating(
            watchlist_id=watchlist_entry.id,
            member_id=member.id,
            score=score,
        )
        self.db.add(rating)
        await self.db.flush()

        return {"success": True, "message": f"{member_name} a note '{movie.title}' {score}/5"}
