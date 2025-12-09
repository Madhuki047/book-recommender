from django.contrib import admin
from .models import Genre, Book, Borrow, UserProfile

admin.site.register(Genre)
admin.site.register(Book)
admin.site.register(Borrow)
admin.site.register(UserProfile)
