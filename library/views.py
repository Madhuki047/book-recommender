from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Book, Genre, Borrow
from .recommender_adapter import get_recommendations_for_user
from collections import defaultdict


def home(request):
    genres = Genre.objects.all()
    selected_slug = request.GET.get("genre")

    books_qs = Book.objects.select_related("genre").order_by("-created_at")

    selected_genre = None
    if selected_slug:
        selected_genre = Genre.objects.filter(slug=selected_slug).first()
        if selected_genre:
            books_qs = books_qs.filter(genre=selected_genre)

    latest_books = list(books_qs)

    # Which books has the current user borrowed, and how did they rate them?
    if request.user.is_authenticated:
        borrows = Borrow.objects.filter(user=request.user)
        borrowed_ids = {b.book_id for b in borrows if b.active}
        user_ratings_dict = {b.book_id: b.rating for b in borrows if b.rating > 0}
    else:
        borrowed_ids = set()
        user_ratings_dict = {}

    # Attach user_rating to each book object for easy use in templates
    for book in latest_books:
        book.user_rating = user_ratings_dict.get(book.id)

    context = {
        "genres": genres,
        "latest_books": latest_books,
        "borrowed_ids": borrowed_ids,
        "selected_genre": selected_genre,
    }
    return render(request, "library/home.html", context)



@login_required
def borrow_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    borrow, created = Borrow.objects.get_or_create(
        user=request.user,
        book=book,
        defaults={"rating": 0},  # unrated initially
    )

    if created:
        messages.success(request, f"You borrowed '{book.title}'.")
    else:
        if borrow.active:
            messages.info(request, f"'{book.title}' is already borrowed.")
        else:
            borrow.active = True
            # keep previous rating; they can re-rate if they want
            borrow.save()
            messages.success(request, f"You borrowed '{book.title}' again.")

    return redirect("library:home")



@login_required
def return_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    try:
        borrow = Borrow.objects.get(user=request.user, book=book)
    except Borrow.DoesNotExist:
        messages.warning(request, "You haven't borrowed that book.")
        return redirect("library:home")

    if not borrow.active:
        messages.info(request, f"You already returned '{book.title}'.")
        return redirect("library:home")

    if borrow.rating <= 0:
        messages.warning(request, "Please use the rating popup to return a book.")
        return redirect("library:home")

    # Rated → now allow return
    borrow.active = False
    borrow.save()
    messages.info(request, f"You returned '{book.title}'.")
    return redirect("library:home")


@login_required
def recommendations(request):
    metric = request.GET.get("metric", "cosine")
    k_text = request.GET.get("k") or None

    try:
        k_neighbours = int(k_text) if k_text is not None else None
    except ValueError:
        k_neighbours = None

    # New recommendations from CF (these are books the user has NOT borrowed before)
    recs = get_recommendations_for_user(
        user=request.user,
        metric=metric,
        k_neighbours=k_neighbours,
        max_results=50,  # a few extra so we have enough per genre
    )

    # Group recommendations by genre
    grouped_recs_dict: dict = defaultdict(list)
    for rec in recs:
        book = rec["book"]
        genre = book.genre
        grouped_recs_dict[genre].append(rec)

    grouped_recs = [
        {"genre": genre, "items": items}
        for genre, items in grouped_recs_dict.items()
    ]
    # sort genres alphabetically
    grouped_recs.sort(key=lambda g: g["genre"].name.lower())

    # "Borrow again" list: all books the user has ever borrowed (rated or not),
    # newest first, no duplicates.
    history_qs = (
        Borrow.objects.filter(user=request.user)
        .select_related("book__genre")
        .order_by("-created_at")
    )
    seen_book_ids = set()
    history_books = []
    for b in history_qs:
        if b.book_id not in seen_book_ids:
            seen_book_ids.add(b.book_id)
            history_books.append(b.book)

    context = {
        "grouped_recs": grouped_recs,
        "history_books": history_books,
        "metric": metric,
        "k_value": k_neighbours,
    }
    return render(request, "library/recommendations.html", context)



@login_required
def rate_and_return_book(request):
    if request.method != "POST":
        return redirect("library:home")

    book_id = request.POST.get("book_id")
    rating_val = request.POST.get("rating")

    try:
        rating_int = int(rating_val)
    except (TypeError, ValueError):
        messages.warning(request, "Invalid rating.")
        return redirect("library:home")

    if not 1 <= rating_int <= 5:
        messages.warning(request, "Rating must be between 1 and 5.")
        return redirect("library:home")

    book = get_object_or_404(Book, pk=book_id)

    borrow, created = Borrow.objects.get_or_create(
        user=request.user,
        book=book,
        defaults={"rating": rating_int, "active": False},
    )

    if not created:
        # Update rating, mark as returned
        borrow.rating = rating_int
        borrow.active = False
        borrow.save()

    messages.success(
        request,
        f"You rated '{book.title}' {rating_int}/5 and returned it.",
    )
    return redirect("library:home")
