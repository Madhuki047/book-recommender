from django.conf import settings
from django.db import models


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=120, blank=True)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE, related_name="books")
    description = models.TextField(blank=True)
    cover = models.ImageField(upload_to="covers/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Borrow(models.Model):
    """
    Represents a user interacting with a book.

    For the recommender we treat 'rating' as strength of preference:
    1–5, default 5 when they borrow.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(default=5)
    active = models.BooleanField(default=True)  # active = currently borrowed

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "book")

    def __str__(self):
        return f"{self.user} → {self.book} ({self.rating})"


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    favourite_genres = models.ManyToManyField(Genre, blank=True)

    def __str__(self):
        return f"Profile({self.user.username})"
