from src.data.ratings_repository import RatingsRepository
from src.recommender.engine import RecommenderEngine
from .models import Borrow, Book


def build_ratings_from_db() -> RatingsRepository:
    """
    Build a RatingsRepository from Borrow records in the DB.

    ratings[user_id][book_id] = rating
    user_id = username, book_id = Book.pk as string.
    """
    repo = RatingsRepository()
    qs = Borrow.objects.all()

    for borrow in qs:
        user_id = borrow.user.username
        book_id = str(borrow.book_id)
        repo.add_rating(user_id, book_id, borrow.rating)

    return repo


def get_recommendations_for_user(
    user,
    metric: str = "cosine",
    k_neighbours: int | None = None,
    max_results: int = 12,
):
    """
    Uses your CF engine from src/ to get recommendations for a Django user.
    Returns a list of dicts: {"book": Book, "score": float, "match_percent": float}
    """
    repo = build_ratings_from_db()
    engine = RecommenderEngine(repo)

    user_id = user.username

    recs = engine.recommend_for_user(
        target_user=user_id,
        metric=metric,
        k_neighbours=k_neighbours,
        max_results=max_results,
    )

    if not recs:
        return []

    max_score = max(score for _, score in recs)
    results = []

    for book_id_str, score in recs:
        try:
            book = Book.objects.get(pk=int(book_id_str))
        except (Book.DoesNotExist, ValueError):
            continue

        match_percent = (score / max_score) * 100.0 if max_score > 0 else 0.0

        results.append(
            {
                "book": book,
                "score": score,
                "match_percent": round(match_percent, 1),
            }
        )

    return results
