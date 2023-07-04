from django.db import models
from utils import utils_time
from utils.utils_require import MAX_CHAR_LENGTH, MAX_TEXT_LENGTH
from UsersApp.models import User
from ImagesApp.models import AronaImage


class CommentManager(models.Manager):
    # 重载 create
    def create(self, *args, **kwargs):
        # 创建该评论
        comment = super().create(*args, **kwargs)
        # 所属图片的评论数加一
        belong_to_image = AronaImage.objects.filter(id=comment.belong_to_image.id).first()
        belong_to_image.comments += 1
        belong_to_image.save()
        # 如果是二级评论
        if comment.is_first_level() is False:
            if comment.reply_to_first_level():
                # 一级评论的评论数加一
                belong_to_comment = Comment.objects.filter(id=comment.belong_to_comment.id).first()
                belong_to_comment.comments += 1
                belong_to_comment.save()
            else:
                # 一级评论的评论数加一
                belong_to_comment = Comment.objects.filter(id=comment.belong_to_comment.id).first()
                belong_to_comment.comments += 1
                belong_to_comment.save()
                # 所回复的二级评论的评论数加一
                reply_to_comment = Comment.objects.filter(id=comment.reply_to_comment.id).first()
                reply_to_comment.comments += 1
                reply_to_comment.save()
        return comment


class Comment(models.Model):
    objects = CommentManager()

    id = models.BigAutoField(primary_key=True)
    content = models.TextField(max_length=MAX_TEXT_LENGTH)
    poster = models.ForeignKey(User, on_delete=models.CASCADE)
    post_time = models.FloatField(default=utils_time.get_timestamp)
    likes = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    belong_to_image = models.ForeignKey(AronaImage, on_delete=models.CASCADE, related_name="image_comments")
    # properties below are not used for first level comments 
    belong_to_comment = models.ForeignKey("self", on_delete=models.CASCADE, default=None, null=True, related_name="belonging_comments")
    reply_to_comment = models.ForeignKey("self", on_delete=models.CASCADE, default=None, null=True, related_name="replying_comments") 
    reply_to_user_username = models.CharField(max_length=MAX_CHAR_LENGTH, default=None, null=True)

    def is_first_level(self):
        return self.belong_to_comment is None
    
    # Only for second level comment
    def reply_to_first_level(self):
        return self.is_first_level() is False and self.belong_to_comment == self.reply_to_comment
    
    def is_liked_by(self, user: User):
        return LikeCommentRelation.objects.filter(user=user, comment=self).exists()
    
    # 重载 delete
    def delete(self, *args, **kwargs):
        if self.is_first_level() is False:
            self.belong_to_image.comments -= 1
            self.belong_to_image.save()
            if self.reply_to_first_level():
                self.belong_to_comment.comments -= 1
                self.belong_to_comment.save()
            else:
                self.belong_to_comment.comments -= 1
                self.belong_to_comment.save()
                if self.reply_to_comment is not None:
                    self.reply_to_comment.comments -= 1
                    self.reply_to_comment.save()
            replies = Comment.objects.filter(reply_to_comment=self)
            for item in replies:
                item.reply_to_comment = None
                item.save()
            super().delete(*args, **kwargs)
        else:
            belongings = Comment.objects.filter(belong_to_comment=self)
            self.belong_to_image.comments -= 1
            self.belong_to_image.save()
            for item in belongings:
                item.delete()
            super().delete(*args, **kwargs)
   
    class Meta:
        indexes = [
            models.Index(fields=['id']),
            models.Index(fields=['belong_to_image']),
            models.Index(fields=['belong_to_comment']),
        ]


class LikeImageRelationManager(models.Manager):
    # 重载 create
    def create(self, *args, **kwargs):
        # 创建该点赞
        relation = super().create(*args, **kwargs)
        # 所属图片的点赞数加一
        belong_to_image = AronaImage.objects.filter(id=relation.image.id).first()
        belong_to_image.likes += 1
        belong_to_image.save()
        return relation
    

class LikeImageRelation(models.Model):
    objects = LikeImageRelationManager()

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ForeignKey(AronaImage, on_delete=models.CASCADE, related_name="image_likes")

    # 重载 delete
    def delete(self, *args, **kwargs):
        # 所属图片的点赞数减一
        belong_to_image = AronaImage.objects.filter(id=self.image.id).first()
        belong_to_image.likes -= 1
        belong_to_image.save()
        # 删除该点赞
        super().delete(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['image']),
        ]


class LikeCommentRelationManager(models.Manager):
    # 重载 create
    def create(self, *args, **kwargs):
        # 创建该点赞
        relation = super().create(*args, **kwargs)
        # 所属评论的点赞数加一
        belong_to_comment = Comment.objects.filter(id=relation.comment.id).first()
        belong_to_comment.likes += 1
        belong_to_comment.save()
        return relation


class LikeCommentRelation(models.Model):
    objects = LikeCommentRelationManager()

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="comment_likes")

    # 重载 delete
    def delete(self, *args, **kwargs):
        # 所属评论的点赞数减一
        belong_to_comment = Comment.objects.filter(id=self.comment.id).first()
        belong_to_comment.likes -= 1
        belong_to_comment.save()
        # 删除该点赞
        super().delete(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['comment']),
        ]