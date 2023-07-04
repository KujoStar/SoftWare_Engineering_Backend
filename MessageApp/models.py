from django.db import models
from utils import utils_time
from utils.utils_require import MAX_TEXT_LENGTH
from UsersApp.models import User


# Create your models here.

class Message(models.Model):
  
  id = models.BigAutoField(primary_key=True)
  time = models.FloatField(default=utils_time.get_timestamp)
  sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
  receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
  content = models.CharField(max_length=MAX_TEXT_LENGTH, default="")
  deleted = models.BooleanField(default=False)
  is_read = models.BooleanField(default=False)
  
  def serialize(self):
    return {
      "id": self.id,
      "time": self.time,
      "is_read": self.is_read,
      "sender": self.sender.serialize(),
      "receiver": self.receiver.serialize(),
      "content": self.content,
    }

  def another(self, user: User):
    return self.sender if self.receiver.username == user.username else self.receiver

  class Meta:
    indexes = [
        models.Index(fields=['id']),
        models.Index(fields=['sender']),
        models.Index(fields=['receiver']),
    ]