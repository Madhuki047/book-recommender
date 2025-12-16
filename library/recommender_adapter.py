from typing import Dict, List

from .models import Borrow, Book
from core.engine import RecommenderEngine


class RatingsBuilder:
    """
    Builds the user → book → rating matrix from the Borrow table.

    ratings[user_id][book_id] = rating
    """

    @staticmethod
    def build() -> Dict[str, Dict[str, float]]:
        ratings: Dict[str, Dict[str, float]] = {}

        for borrow in Borrow.objects.filter(rating__gt=0):
            user = borrow.user.username
            book = str(borrow.book_id)
            rating = float(borrow.rating)

            user_ratings = ratings.setdefault(user, {})
            user_ratings[book] = rating

        return ratings


class RecommendationService:
    """
    High-level façade used by the Django views.

    Wraps RecommenderEngine and applies bookstore-specific rules
    such as hiding books the user has already borrowed.
    """

    def __init__(self, user):
        self.user = user

    def get_recommendations(
        self,
        metric: str = "cosine",
        k_neighbours: int | None = None,
        max_results: int = 12,
    ) -> List[dict]:
        # 1) Build ratings matrix from all users
        ratings = RatingsBuilder.build()
        user_id = self.user.username

        if user_id not in ratings:
            return []

        # 2) Run collaborative filtering
        engine = RecommenderEngine(ratings)
        raw_recs = engine.recommend_for_user(
            target_user=user_id,
            metric=metric,
            k_neighbours=k_neighbours,
            max_results=max_results,
        )
        if not raw_recs:
            return []

        # 3) Exclude any book this user has EVER borrowed (active or past)
        seen_ids = set(
            Borrow.objects.filter(user=self.user).values_list("book_id", flat=True)
        )

        filtered: List[tuple[int, float]] = []
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

        # 4) Convert scores into % match (60–100%) for the UI
        scores = [s for _, s in filtered]
        max_score = max(scores)
        min_score = min(scores)
        n = len(filtered)

        results: List[dict] = []

        for idx, (book_id, score) in enumerate(filtered):
            try:
                book = Book.objects.get(pk=book_id)
            except Book.DoesNotExist:
                continue

            if max_score > min_score:
                # normalised between 60 and 100%
                pct = 60.0 + 40.0 * (score - min_score) / (max_score - min_score)
            else:
                # all scores equal → spread evenly 100 → 60 by rank
                pct = 100.0 if n == 1 else 100.0 - (idx / (n - 1)) * 40.0

            results.append(
                {
                    "book": book,
                    "score": score,
                    "match_percent": round(pct, 1),
                }
            )

        return results


# --------------------------------------------------------------------
# Backwards-compatible function-style API used elsewhere in the project
# --------------------------------------------------------------------


def build_ratings() -> Dict[str, Dict[str, float]]:
    """
    Legacy function name kept for compatibility.

    Internally delegates to RatingsBuilder.build().
    """
    return RatingsBuilder.build()


def get_recommendations_for_user(
    user,
    metric: str = "cosine",
    k_neighbours: int | None = None,
    max_results: int = 12,
) -> List[dict]:
    """
    Legacy function used by views.recommendations().

    Internally delegates to RecommendationService so you can
    show the class on your diagrams without breaking code.
    """
    service = RecommendationService(user)
    return service.get_recommendations(
        metric=metric,
        k_neighbours=k_neighbours,
        max_results=max_results,
    )