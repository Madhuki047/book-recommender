from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Book, Genre, Borrow
from core.engine import RecommenderEngine
from .recommender_adapter import get_recommendations_for_user, build_ratings

from collections import defaultdict
import time
import random
import math



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
        k_neighbours = int(k_text) if k_text not in (None, "") else None
    except ValueError:
        k_neighbours = None

    # Main recommendations
    recs = get_recommendations_for_user(
        user=request.user,
        metric=metric,
        k_neighbours=k_neighbours,
        max_results=24,
    )

    # Group by genre for “Adventure / Mystery / …” headings
    grouped = defaultdict(list)
    for rec in recs:
        grouped[rec["book"].genre].append(rec)

    grouped_recs = [
        {"genre": genre, "items": items}
        for genre, items in grouped.items()
    ]
    grouped_recs.sort(key=lambda g: g["genre"].name)

    # Borrow-again: distinct books the user has ever borrowed
    history_qs = (
        Borrow.objects.filter(user=request.user)
        .select_related("book", "book__genre")
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

    # If this is an AJAX “partial” request, return only the recs fragment
    if request.GET.get("partial") == "1":
        return render(request, "library/_recommendations_partial.html", context)

    # Normal full-page render
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



@login_required
def algorithm_insights(request):
    # 1) Build current ratings matrix from DB
    ratings = build_ratings()
    num_users = len(ratings)
    all_book_ids = {book_id for user_r in ratings.values() for book_id in user_r.keys()}
    num_books = len(all_book_ids)
    num_ratings = sum(len(user_r) for user_r in ratings.values())

    # 2) Live performance for this user: cosine vs jaccard
    metrics = ["cosine", "jaccard"]
    live_results = []

    if request.user.username in ratings:
        engine = RecommenderEngine(ratings)
        for metric_name in metrics:
            start = time.perf_counter()
            recs = engine.recommend_for_user(
                target_user=request.user.username,
                metric=metric_name,
                k_neighbours=None,
                max_results=20,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            live_results.append(
                {
                    "metric": metric_name,
                    "time_ms": elapsed_ms,
                    "count": len(recs),
                }
            )

    # 3) Synthetic benchmark: compare cosine vs jaccard on the same random matrices
    bench_sizes = [
        (10, 20),
        (20, 50),
        (50, 100),
    ]
    bench_labels = []
    bench_cosine = []
    bench_jaccard = []

    rng = random.Random(42)

    for u_count, b_count in bench_sizes:
        # Build random rating matrix
        synth_ratings = {}
        for i in range(u_count):
            user_id = f"U{i}"
            user_ratings = {}
            for j in range(b_count):
                if rng.random() < 0.4:  # 40% chance user rated book j
                    user_ratings[str(j)] = rng.randint(1, 5)
            synth_ratings[user_id] = user_ratings

        engine_synth = RecommenderEngine(synth_ratings)
        target = "U0"

        # Cosine
        start = time.perf_counter()
        _ = engine_synth.recommend_for_user(
            target_user=target,
            metric="cosine",
            k_neighbours=None,
            max_results=20,
        )
        cosine_ms = (time.perf_counter() - start) * 1000.0

        # Jaccard
        start = time.perf_counter()
        _ = engine_synth.recommend_for_user(
            target_user=target,
            metric="jaccard",
            k_neighbours=None,
            max_results=20,
        )
        jaccard_ms = (time.perf_counter() - start) * 1000.0

        bench_labels.append(f"{u_count}×{b_count}")
        bench_cosine.append(cosine_ms)
        bench_jaccard.append(jaccard_ms)

    # 4) Flatten ratings dict for nice display
    ratings_users = sorted(ratings.keys())
    ratings_rows = []
    for u in ratings_users:
        user_r = ratings.get(u, {})
        pairs = sorted(user_r.items(), key=lambda x: x[0])
        ratings_rows.append(
            {
                "user": u,
                "pairs": pairs,
            }
        )

    # 5) Raw similarity numbers: current user vs others
    similarity_rows = []
    if request.user.username in ratings and len(ratings_users) > 1:
        engine_full = RecommenderEngine(ratings)
        target = request.user.username

        for other in ratings_users:
            if other == target:
                continue
            cos_val = engine_full.user_similarity(target, other, metric="cosine")
            jac_val = engine_full.user_similarity(target, other, metric="jaccard")
            similarity_rows.append(
                {
                    "user": other,
                    "cosine": cos_val,
                    "jaccard": jac_val,
                }
            )

        similarity_rows.sort(key=lambda r: r["cosine"], reverse=True)

    # 6) k-neighbour sweep for THIS user (cosine only)
    k_labels = []
    k_times = []
    k_counts = []
    k_rows = []

    if request.user.username in ratings:
        engine_k = RecommenderEngine(ratings)
        k_values = [1, 2, 3, 5, 10, None]
        for k in k_values:
            label = "all" if k is None else str(k)
            start = time.perf_counter()
            recs = engine_k.recommend_for_user(
                target_user=request.user.username,
                metric="cosine",
                k_neighbours=k,
                max_results=20,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            k_labels.append(label)
            k_times.append(elapsed_ms)
            k_counts.append(len(recs))

        # Build rows for template table
        for label, t, c in zip(k_labels, k_times, k_counts):
            k_rows.append(
                {
                    "k": label,
                    "time_ms": t,
                    "count": c,
                }
            )

    context = {
        "num_users": num_users,
        "num_books": num_books,
        "num_ratings": num_ratings,
        "live_results": live_results,
        "bench_labels": bench_labels,
        "bench_cosine": bench_cosine,
        "bench_jaccard": bench_jaccard,
        "ratings_rows": ratings_rows,
        "similarity_rows": similarity_rows,
        "k_labels": k_labels,
        "k_times": k_times,
        "k_counts": k_counts,
        "k_rows": k_rows,
    }
    return render(request, "library/algorithm_insights.html", context)

@login_required
def borrowed_items(request):
    # All *currently active* borrows for this user
    borrows = (
        Borrow.objects
        .filter(user=request.user, active=True)
        .select_related("book", "book__genre")
        .order_by("-created_at")
    )

    context = {
        "borrows": borrows,
    }
    return render(request, "library/borrowed_items.html", context)