from typing import Dict, List, Tuple, Optional, Callable

from src.data.ratings_repository import RatingsRepository
from src.recommender.similarity import (
    RatingsDict,
    cosine_similarity,
    jaccard_similarity,
)


SimilarityFunc = Callable[[RatingsDict, str, str], float]


class RecommenderEngine:
    """
    User-based collaborative filtering recommender.

    - Can use cosine or Jaccard similarity between users.
    - Optionally restricts to top-k most similar users (kNN style).
    """

    def __init__(self, ratings_repo: RatingsRepository) -> None:
        self.ratings_repo = ratings_repo

    def _get_similarity_function(
        self,
        metric: str,
        positive_threshold: float = 0.0,
    ) -> SimilarityFunc:
        """
        Return a similarity function based on the metric name.
        """

        metric_lower = metric.lower()

        if metric_lower == "cosine":
            # Directly use cosine function
            return cosine_similarity

        if metric_lower == "jaccard":
            # Wrap jaccard with the threshold we want
            def sim(ratings: RatingsDict, u1: str, u2: str) -> float:
                return jaccard_similarity(
                    ratings,
                    u1,
                    u2,
                    positive_threshold=positive_threshold,
                )

            return sim

        raise ValueError(f"Unknown similarity metric: {metric}")

    def _compute_similarities(
        self,
        target_user: str,
        metric: str = "cosine",
        positive_threshold: float = 0.0,
    ) -> Dict[str, float]:
        """
        Compute similarity between target_user and all other users
        using the given metric.
        """
        ratings = self.ratings_repo.ratings

        if target_user not in ratings:
            raise ValueError(f"Unknown user: {target_user}")

        similarity_func = self._get_similarity_function(
            metric, positive_threshold
        )

        similarities: Dict[str, float] = {}

        for user_id in ratings:
            if user_id == target_user:
                continue

            sim = similarity_func(ratings, target_user, user_id)
            if sim > 0:
                similarities[user_id] = sim

        return similarities

    def recommend_for_user(
        self,
        target_user: str,
        metric: str = "cosine",
        k_neighbours: Optional[int] = None,
        max_results: int = 5,
        positive_threshold: float = 0.0,
    ) -> List[Tuple[str, float]]:
        """
        Recommend books for the target_user.

        Returns a list of (book_id, score) sorted by score descending.

        :param target_user: user id to recommend for.
        :param metric: 'cosine' or 'jaccard'.
        :param k_neighbours: if given, only use top-k most similar users.
        :param max_results: number of books to return.
        :param positive_threshold: used only for Jaccard to define 'liked' books.
        """

        ratings = self.ratings_repo.ratings

        if target_user not in ratings:
            raise ValueError(f"Unknown user: {target_user}")

        # 1) Compute similarity to all other users
        similarities = self._compute_similarities(
            target_user=target_user,
            metric=metric,
            positive_threshold=positive_threshold,
        )

        if not similarities:
            # No similar users found -> no collaborative recommendation
            return []

        # 2) Sort by similarity (highest first)
        similar_users = sorted(
            similarities.items(), key=lambda x: x[1], reverse=True
        )

        # take top-k neighbours if requested
        if k_neighbours is not None:
            similar_users = similar_users[:k_neighbours]

        # 3) Weighted sum of neighbours' ratings
        target_ratings = ratings[target_user]
        scores: Dict[str, float] = {}

        for neighbour_id, sim in similar_users:
            neighbour_ratings = ratings[neighbour_id]

            for book_id, rating in neighbour_ratings.items():
                # Only consider books that target_user hasn't rated / read
                if target_ratings.get(book_id, 0) == 0:
                    scores[book_id] = scores.get(book_id, 0.0) + sim * rating

        # 4) Sort recommendations by score
        ranked_books = sorted(
            scores.items(), key=lambda x: x[1], reverse=True
        )

        if max_results is not None:
            ranked_books = ranked_books[:max_results]

        return ranked_books
