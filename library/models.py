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
    For now this is mainly for the recommender later.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "book")

    def __str__(self):
        return f"{self.user} → {self.book} ({self.rating})"
