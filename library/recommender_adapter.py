from typing import Dict, List

from .models import Borrow, Book
from core.engine import RecommenderEngine


def build_ratings() -> Dict[str, Dict[str, float]]:
    ratings: Dict[str, Dict[str, float]] = {}

    for borrow in Borrow.objects.filter(rating__gt=0):
        user = borrow.user.username
        book = str(borrow.book_id)
        rating = float(borrow.rating)

        if user not in ratings:
            ratings[user] = {}
        ratings[user][book] = rating

    return ratings


def get_recommendations_for_user(
    user,
    metric: str = "cosine",
    k_neighbours: int | None = None,
    max_results: int = 12,
) -> List[dict]:
    ratings = build_ratings()
    user_id = user.username

    if user_id not in ratings:
        return []

    engine = RecommenderEngine(ratings)
    raw_recs = engine.recommend_for_user(
        target_user=user_id,
        metric=metric,
        k_neighbours=k_neighbours,
        max_results=max_results,
    )

    if not raw_recs:
        return []

    # Exclude any book this user has EVER borrowed (active or past)
    seen_ids = set(
        Borrow.objects.filter(user=user).values_list("book_id", flat=True)
    )
    filtered = []
    for book_id_str, score in raw_recs:
        try:
            book_id_int = int(book_id_str)
        except ValueError:
            continue
        if book_id_int in seen_ids:
            continue
        filtered.append((book_id_int, score))

    if not filtered:
        return []

    scores = [s for _, s in filtered]
    max_score = max(scores)
    min_score = min(scores)

    results: List[dict] = []

    for idx, (book_id, score) in enumerate(filtered):
        try:
            book = Book.objects.get(pk=book_id)
        except Book.DoesNotExist:
            continue

        # If scores differ, normalise properly
        if max_score > min_score:
            pct = 60.0 + 40.0 * (score - min_score) / (max_score - min_score)
        else:
            # All scores equal → spread by rank between 100 and 60
            n = len(filtered)
            if n == 1:
                pct = 100.0
            else:
                pct = 100.0 - (idx / (n - 1)) * 40.0

        results.append(
            {
                "book": book,
                "score": score,
                "match_percent": round(pct, 1),
            }
        )

    return results