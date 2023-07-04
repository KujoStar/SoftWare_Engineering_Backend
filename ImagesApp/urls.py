from django.urls import path, re_path, include
import ImagesApp.views as views

urlpatterns = [
    path("semiupload", views.semiupload),
    path("upload", views.upload_image),
    path("category", views.image_category),
    path("convert", views.video2gif),
    path("resolution", views.super_resolution),
    path("watermark", views.watermark),
    path("utilities", views.util_results),
    path("<int:id>", views.image_info),
    path("<int:id>/download", views.download_image),
    path("raw/<str:hash>", views.image),
    path("rough/<str:hash>", views.rough_image),
    path("<int:id>/comments", views.image_comments),
]
