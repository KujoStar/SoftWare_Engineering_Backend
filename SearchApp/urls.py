from django.urls import path, re_path, include
import SearchApp.views as views

urlpatterns = [
    path("images", views.search_image),
    path("history", views.search_history),
    path("user", views.search_user),
]