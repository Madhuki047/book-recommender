import math
from typing import Dict

# ratings[user_id][item_id] = numeric rating
RatingsDict = Dict[str, Dict[str, float]]


def cosine_similarity(ratings: RatingsDict, user1: str, user2: str) -> float:
    """
    Cosine similarity between two users based on their ratings.

    Only considers items rated by BOTH users.
    """
    items1 = ratings.get(user1, {})
    items2 = ratings.get(user2, {})

    common_items = set(items1.keys()) & set(items2.keys())
    if not common_items:
        return 0.0

    dot = sum(items1[i] * items2[i] for i in common_items)
    mag1 = math.sqrt(sum(items1[i] ** 2 for i in common_items))
    mag2 = math.sqrt(sum(items2[i] ** 2 for i in common_items))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot / (mag1 * mag2)


def _liked_items(
    ratings: RatingsDict,
    user: str,
    threshold: float = 0.0,
) -> set[str]:
    """
    Helper: items considered 'liked' by a user (rating > threshold).
    """
    return {
        item_id
        for item_id, r in ratings.get(user, {}).items()
        if r > threshold
    }


def jaccard_similarity(
    ratings: RatingsDict,
    user1: str,
    user2: str,
    threshold: float = 0.0,
) -> float:
    """
    Jaccard similarity based on sets of liked items.

      J(A,B) = |A ∩ B| / |A ∪ B|
    """
    set1 = _liked_items(ratings, user1, threshold)
    set2 = _liked_items(ratings, user2, threshold)

    if not set1 and not set2:
        return 0.0

    inter = len(set1 & set2)
    union = len(set1 | set2)

    if union == 0:
        return 0.0

    return inter / union
