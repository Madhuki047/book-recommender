import math
from typing import Dict

# ratings[user_id][book_id] = rating
RatingsDict = Dict[str, Dict[str, float]]


def cosine_similarity(ratings: RatingsDict, user1: str, user2: str) -> float:
    """
    Compute cosine similarity between two users.
    Uses only books that both users have rated.
    """
    common_books = set(ratings[user1].keys()) & set(ratings[user2].keys())

    if not common_books:
        return 0.0

    dot_product = sum(
        ratings[user1][book] * ratings[user2][book] for book in common_books
    )
    magnitude1 = math.sqrt(
        sum(ratings[user1][book] ** 2 for book in common_books)
    )
    magnitude2 = math.sqrt(
        sum(ratings[user2][book] ** 2 for book in common_books)
    )

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


def _user_book_set(
    ratings: RatingsDict,
    user: str,
    positive_threshold: float = 0.0,
) -> set[str]:
    """
    Build a set of 'liked' books for a user.

    A book is 'liked' if its rating is > positive_threshold.
    For simple 0/positive ratings, threshold = 0 works fine.
    """
    return {
        book_id
        for book_id, score in ratings[user].items()
        if score > positive_threshold
    }


def jaccard_similarity(
    ratings: RatingsDict,
    user1: str,
    user2: str,
    positive_threshold: float = 0.0,
) -> float:
    """
    Jaccard similarity between two users based on the set of books they liked.

    J(A, B) = |A ∩ B| / |A ∪ B|
    """
    set1 = _user_book_set(ratings, user1, positive_threshold)
    set2 = _user_book_set(ratings, user2, positive_threshold)

    if not set1 and not set2:
        return 0.0

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    if union == 0:
        return 0.0

    return intersection / union
