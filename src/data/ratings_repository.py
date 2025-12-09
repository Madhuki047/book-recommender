from typing import Dict


class RatingsRepository:
    """
    Stores user-book ratings.

    Internally:
        ratings[user_id][book_id] = rating (int or float)

    In this project, we treat:
        0 or missing  -> not borrowed / not liked
        >0            -> user has interacted with / liked / borrowed the book
    """

    def __init__(self) -> None:
        self.ratings: Dict[str, Dict[str, float]] = {}

    def ensure_user(self, user_id: str) -> None:
        if user_id not in self.ratings:
            self.ratings[user_id] = {}

    def add_rating(self, user_id: str, book_id: str, rating: float) -> None:
        self.ensure_user(user_id)
        self.ratings[user_id][book_id] = float(rating)

    def get_all_users(self) -> list[str]:
        return list(self.ratings.keys())

    def get_user_ratings(self, user_id: str) -> Dict[str, float]:
        return self.ratings.get(user_id, {})

    def has_user(self, user_id: str) -> bool:
        return user_id in self.ratings

    # ----- Borrow / return helpers -----

    def get_rating(self, user_id: str, book_id: str) -> float:
        return self.ratings.get(user_id, {}).get(book_id, 0.0)

    def set_rating(self, user_id: str, book_id: str, rating: float) -> None:
        self.ensure_user(user_id)
        self.ratings[user_id][book_id] = float(rating)

    def borrow_book(self, user_id: str, book_id: str) -> None:
        """
        User borrows a book.

        For simplicity we treat a borrow as a strong positive rating.
        """
        self.set_rating(user_id, book_id, 5.0)

    def return_book(self, user_id: str, book_id: str) -> None:
        """
        User returns a book.

        We keep history very simple: we just set rating back to 0.
        """
        self.set_rating(user_id, book_id, 0.0)