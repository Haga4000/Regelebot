"""Seed script to populate the database with sample data for testing."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bot" / "src"))

from core.database import get_db  # noqa: E402
from models.member import Member  # noqa: E402
from models.movie import Movie  # noqa: E402
from models.rating import Rating  # noqa: E402
from models.watchlist import Watchlist  # noqa: E402


async def seed():
    async with get_db() as db:
        # Create members
        members = [
            Member(phone_hash="member_marie", display_name="Marie"),
            Member(phone_hash="member_paul", display_name="Paul"),
            Member(phone_hash="member_lucas", display_name="Lucas"),
        ]
        for m in members:
            db.add(m)
        await db.flush()

        # Create movies
        movies_data = [
            {"tmdb_id": 27205, "title": "Inception", "original_title": "Inception", "year": 2010, "genres": ["Action", "Science-Fiction", "Aventure"]},
            {"tmdb_id": 496243, "title": "Parasite", "original_title": "기생충", "year": 2019, "genres": ["Thriller", "Drame", "Comedie"]},
            {"tmdb_id": 438631, "title": "Dune", "original_title": "Dune", "year": 2021, "genres": ["Science-Fiction", "Aventure"]},
        ]
        movies = []
        for md in movies_data:
            m = Movie(**md)
            db.add(m)
            movies.append(m)
        await db.flush()

        # Create watchlist entries
        watchlist_entries = []
        for movie in movies:
            w = Watchlist(movie_id=movie.id)
            db.add(w)
            watchlist_entries.append(w)
        await db.flush()

        # Create ratings
        ratings_data = [
            (0, 0, 5), (0, 1, 4), (0, 2, 4),  # Inception
            (1, 0, 5), (1, 1, 5), (1, 2, 5),  # Parasite
            (2, 0, 4), (2, 1, 5), (2, 2, 4),  # Dune
        ]
        for wi, mi, score in ratings_data:
            r = Rating(
                watchlist_id=watchlist_entries[wi].id,
                member_id=members[mi].id,
                score=score,
            )
            db.add(r)

        await db.flush()
        print("Database seeded with sample data!")
        print(f"  {len(members)} members")
        print(f"  {len(movies)} movies")
        print(f"  {len(watchlist_entries)} watchlist entries")
        print(f"  {len(ratings_data)} ratings")


if __name__ == "__main__":
    asyncio.run(seed())
