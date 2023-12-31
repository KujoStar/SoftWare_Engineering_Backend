from django.db import models
from django.contrib.postgres import fields as postgres_models
from UsersApp.models import User
from datetime import timedelta
from utils import utils_time
from utils.utils_require import MAX_CHAR_LENGTH, MAX_TEXT_LENGTH


class AronaImage(models.Model):
    """The image model.

    Attributes:
        id: the auto-incremented ID of the GIF, serving as the primary key.
        hash: the hash value of the GIF, generated by blake3.
        uploader: the uploader of the GIF, i.e. the UUID of the user who uploaded the GIF.
        upload_time: the upload time of the GIF, i.e. the timestamp when the GIF is uploaded.
    """
    id = models.BigAutoField(primary_key=True)
    content_type = models.CharField(max_length=MAX_CHAR_LENGTH) # in [jpeg, png, gif]
    hash = models.CharField(max_length=MAX_CHAR_LENGTH)
    uploader = models.ForeignKey(User, on_delete=models.CASCADE, related_name="uploaded_images")
    upload_time = models.FloatField(default=utils_time.get_timestamp)
    width = models.IntegerField()
    height = models.IntegerField()
    likes = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    title = models.CharField(max_length=MAX_CHAR_LENGTH, default="Untitled")
    tags = postgres_models.ArrayField(models.CharField(max_length=MAX_CHAR_LENGTH), default=list)
    description = models.TextField(max_length=MAX_TEXT_LENGTH, default=str)
    category = models.CharField(max_length=MAX_CHAR_LENGTH, default="Uncategorized")

    def is_liked_by(self, user: User):
        from SocialApp.models import LikeImageRelation
        return LikeImageRelation.objects.filter(user=user, image=self).exists()

    class Meta:
        indexes = [
            models.Index(fields=['id']),
            models.Index(fields=['hash']),
        ]


class AronaImageBrowseRecord(models.Model):
    """The browse record of the image.

    Attributes:
        id: the auto-incremented ID of the browse record, serving as the primary key.
        image: the ID of the image.
        browser: the UUID of the user who browsed the image.
        browse_time: the timestamp when the image is browsed.
    """
    id = models.BigAutoField(primary_key=True)
    image = models.ForeignKey(AronaImage, on_delete=models.CASCADE)
    browser = models.ForeignKey(User, on_delete=models.CASCADE, related_name="browse_records")
    browse_time = models.FloatField(default=utils_time.get_timestamp)

    class Meta:
        indexes = [
            models.Index(fields=['id']),
            models.Index(fields=['browser']),
        ]


class ImageUtilRecord(models.Model):
    """The record of usage of image utilities.

    Attributes:
        id: the auto-incremented ID of the record, serving as the primary key.
        user: the user who took usage of the utility.
        result_url: the URL of the result file of the utility.
        util_type: the type of the utility.
    """
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="util_records")
    result_url = models.CharField(max_length=MAX_TEXT_LENGTH)
    result_type = models.CharField(max_length=MAX_CHAR_LENGTH)
    util_type = models.CharField(max_length=MAX_CHAR_LENGTH)
    finish_time = models.FloatField(default=utils_time.get_timestamp)
    expiry = models.FloatField(default=timedelta(days=7).total_seconds())

    class Meta:
        indexes = [
            models.Index(fields=['id']),
            models.Index(fields=['user']),
        ]