from django.urls import path, re_path, include
import UsersApp.views as views

urlpatterns = [
    path('test', views.test),
    path('login', views.login),
    path('prelogin', views.prelogin),
    path('register', views.register),
    path('preregister', views.preregister),
    path('records', views.records),
    path('user/<username>', views.user_info),
    path('user/<username>/detail', views.user_info),
    path('user/<username>/follower', views.user_info),
    path('user/<username>/following', views.user_info),
    path('user/<username>/follow', views.user_info),
    path('user/<username>/unfollow', views.user_info),
    path('user/<username>/images', views.user_image_info),
]
