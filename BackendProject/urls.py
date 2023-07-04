from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include("UsersApp.urls")),
    path('image/', include("ImagesApp.urls")),
    path('social/', include("SocialApp.urls")),
    path('search/', include("SearchApp.urls")),
    path('message/', include("MessageApp.urls"))
]
