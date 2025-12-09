from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Book, Genre, Borrow
from .recommender_adapter import get_recommendations_for_user


def home(request):
    genres = Genre.objects.all()
    latest_books = Book.objects.select_related("genre").order_by("-created_at")[:8]

    context = {
        "genres": genres,
        "latest_books": latest_books,
    }
    return render(request, "library/home.html", context)


@login_required
def borrow_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    borrow, created = Borrow.objects.get_or_create(
        user=request.user,
        book=book,
        defaults={"rating": 5},
    )
    if not created:
        borrow.active = True
        borrow.rating = 5
        borrow.save()

    messages.success(request, f"You borrowed '{book.title}'.")
    return redirect("library:home")


@login_required
def return_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    try:
        borrow = Borrow.objects.get(user=request.user, book=book)
        borrow.active = False
        borrow.rating = 0
        borrow.save()
        messages.info(request, f"You returned '{book.title}'.")
    except Borrow.DoesNotExist:
        messages.warning(request, "You haven't borrowed that book.")

    return redirect("library:home")


@login_required
def recommendations(request):
    metric = request.GET.get("metric", "cosine")
    k = request.GET.get("k") or None
    try:
        k_neighbours = int(k) if k is not None else None
    except ValueError:
        k_neighbours = None

    recs = get_recommendations_for_user(
        user=request.user,
        metric=metric,
        k_neighbours=k_neighbours,
        max_results=12,
    )

    context = {
        "recommendations": recs,
        "metric": metric,
        "k_value": k_neighbours,
    }
    return render(request, "library/recommendations.html", context)
