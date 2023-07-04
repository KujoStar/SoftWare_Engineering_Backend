from django.urls import path, re_path, include
import SocialApp.views as views

urlpatterns = [
    path("comment", views.post_comment),
    path("comment/<int:id>", views.comment_info),
    path("like/image/<int:id>", views.like_image),
    path("like/comment/<int:id>", views.like_comment),
    path("dynamic/list", views.dynamic_list),
    path("dynamic/unread", views.dynamic_unread),
]