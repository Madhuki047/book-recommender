from django.urls import path
from . import views

app_name = "library"

urlpatterns = [
    path("", views.home, name="home"),
    path("books/<int:pk>/borrow/", views.borrow_book, name="borrow_book"),
    path("books/<int:pk>/return/", views.return_book, name="return_book"),
    path("recommendations/", views.recommendations, name="recommendations"),
]
