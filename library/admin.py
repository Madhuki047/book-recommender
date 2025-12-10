from django.contrib import admin
from .models import Genre, Book, Borrow


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "genre", "author")
    list_filter = ("genre",)
    search_fields = ("title", "author")


@admin.register(Borrow)
class BorrowAdmin(admin.ModelAdmin):
    list_display = ("user", "book", "rating", "active", "created_at")
    list_filter = ("active", "rating", "created_at", "book__genre")
    search_fields = ("user__username", "book__title")
