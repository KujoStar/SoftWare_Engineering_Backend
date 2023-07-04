from django.urls import path, re_path, include
import MessageApp.views as views

urlpatterns = [
    path("record", views.record),
    path("send", views.send),
    path("recent", views.recent),
    path("unread", views.unread),
]