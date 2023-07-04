from django.db import models
from utils import utils_time
from utils.utils_require import MAX_CHAR_LENGTH, MAX_TEXT_LENGTH
from UsersApp.models import User
# Create your models here.

class SearchModel(models.Model):
    id = models.BigAutoField(primary_key=True)
    search_for = models.TextField(max_length=MAX_TEXT_LENGTH, default=str)
    search_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="search_records")
    search_time = models.FloatField(default=utils_time.get_timestamp)
    deleted = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=["search_user"]),
        ]