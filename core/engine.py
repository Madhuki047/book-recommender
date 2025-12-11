from typing import Dict, List, Tuple, Optional, Callable

from .similarity import (
    RatingsDict,
    cosine_similarity,
    jaccard_similarity,
)


SimilarityFunc = Callable[[RatingsDict, str, str], float]


class RecommenderEngine:
    """
    User-based collaborative filtering.

    - Supports 'cosine' and 'jaccard' similarity.
    - Can limit to top-k neighbours.
    """

    def __init__(self, ratings: RatingsDict) -> None:
        self.ratings = ratings

    # --- internal helpers ---

    def _get_similarity_function(
        self,
        metric: str,
        jaccard_threshold: float = 0.0,
    ) -> SimilarityFunc:
        metric = metric.lower()

        if metric == "cosine":
            return cosine_similarity

        if metric == "jaccard":

            def sim(r: RatingsDict, u1: str, u2: str) -> float:
                return jaccard_similarity(r, u1, u2, threshold=jaccard_threshold)

            return sim

        raise ValueError(f"Unknown similarity metric: {metric}")

    def _compute_similarities(
        self,
        target_user: str,
        metric: str,
        jaccard_threshold: float = 0.0,
    ) -> Dict[str, float]:
        """
        Similarity between target_user and every other user.
        """
        if target_user not in self.ratings:
            # target has no history
            return {}

        sim_func = self._get_similarity_function(metric, jaccard_threshold)
        similarities: Dict[str, float] = {}

        for other in self.ratings:
            if other == target_user:
                continue

            s = sim_func(self.ratings, target_user, other)
            if s > 0:
                similarities[other] = s

        return similarities

    # --- public API ---

    def recommend_for_user(
        self,
        target_user: str,
        metric: str = "cosine",
        k_neighbours: Optional[int] = None,
        max_results: int = 12,
        jaccard_threshold: float = 0.0,
    ) -> List[Tuple[str, float]]:
        """
        Recommend items (books) for target_user.

        Returns: list of (item_id, score) sorted by score desc.
        """
        if target_user not in self.ratings:
            return []

        similarities = self._compute_similarities(
            target_user=target_user,
            metric=metric,
            jaccard_threshold=jaccard_threshold,
        )
        if not similarities:
            return []

        # sort users by similarity
        neighbours = sorted(
            similarities.items(), key=lambda x: x[1], reverse=True
        )

        if k_neighbours is not None:
            neighbours = neighbours[:k_neighbours]

        target_ratings = self.ratings[target_user]
        scores: Dict[str, float] = {}

        for neighbour_id, sim in neighbours:
            neighbour_ratings = self.ratings[neighbour_id]
            for item_id, rating in neighbour_ratings.items():
                # only items the target hasn't interacted with
                if target_ratings.get(item_id, 0) == 0:
                    scores[item_id] = scores.get(item_id, 0.0) + sim * rating

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:max_results]


    def user_similarity(self, user1: str, user2: str, metric: str = "cosine") -> float:
        """
        Wraps calls to the standalone similarity functions.
        """
        if metric == "cosine":
            return cosine_similarity(self.ratings, user1, user2)
        elif metric == "jaccard":
            return jaccard_similarity(self.ratings, user1, user2)
        else:
            raise ValueError(f"Unknown similarity metric: {metric}")
