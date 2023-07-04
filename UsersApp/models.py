from django.db import models
from utils import utils_time
from utils.utils_require import MAX_CHAR_LENGTH
# Create your models here.

class User(models.Model):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=MAX_CHAR_LENGTH, unique=True)
    password = models.CharField(max_length=MAX_CHAR_LENGTH, default="")
    email = models.CharField(max_length=MAX_CHAR_LENGTH, default="")
    mail_code = models.CharField(max_length=MAX_CHAR_LENGTH, default="")
    salt = models.CharField(max_length=MAX_CHAR_LENGTH, default="")
    nickname = models.CharField(max_length=MAX_CHAR_LENGTH, default="")
    registerTime = models.FloatField(default=utils_time.get_timestamp)
    userType = models.CharField(max_length=MAX_CHAR_LENGTH, default="user")
    slogan = models.CharField(max_length=MAX_CHAR_LENGTH, default="114514")
    followingCount = models.IntegerField(default=0)
    followerCount = models.IntegerField(default=0)
    uploadCount = models.IntegerField(default=0)
    last_view_folllowing_moment = models.FloatField(default=0.0)
    
    class Meta:
        indexes = [models.Index(fields=["username"])]
        
    def serialize(self):
        return {
            "username": self.username,
            "email": self.email,
            "nickname": self.nickname,
            "registerTime": self.registerTime,
            "userType": self.userType,
            "slogan": self.slogan,
            "followingCount": self.followingCount,
            "followerCount": self.followerCount,
            "uploadCount": self.uploadCount
        }

class FollowRelation(models.Model):
    follower = models.CharField(max_length=MAX_CHAR_LENGTH, default="")
    following = models.CharField(max_length=MAX_CHAR_LENGTH, default="")