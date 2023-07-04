import random
from PIL import Image
from urllib.request import urlopen
from django.test import RequestFactory, TestCase
from ImagesApp.models import AronaImage
from SocialApp.models import Comment
from UsersApp.models import User
from ImagesApp.views import IMAGE_CATEGORIES
from SearchApp.models import SearchModel
from .views import *
import json
import os
# Create your tests here.
# Create your tests here.
class MessageTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.jwt = os.getenv("TEST_JWT")# for real unit-test

    def setupuser(self, username, password, email):
        if not User.objects.filter(username = username).exists():
            user = User(username = username, password = password, email = email)
            user.save()

    def illegalize_jwt(self, jw_token: str) -> str:
        header, payload, signature = jw_token.split(".")
        signature = list(signature)
        rand_index = random.randint(0, len(signature) - 1)
        del signature[rand_index]
        signature = "".join(signature)
        return f"{header}.{payload}.{signature}"
    
    def send_message(self, receiver, content, jwt):
        data = {
            "content": content
        }
        data = {k: v for k, v in data.items() if v is not None}
        request = self.factory.post(f"/message/send?username={receiver}", data=data, content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {jwt}")
        response = send(request)
        return response
    
    def get_history(self, another, jwt):
        request = self.factory.get(f"/message/record?username={another}", content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {jwt}")
        response = record(request)
        return response
    
    def test_send_message_with_no_receiver(self):
        request = self.factory.post(f"/message/send?username", data={
            "content": "114514"
        }, content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {self.jwt}")
        response = send(request)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(json_response['msg'], "User not found")

    def test_send_message_with_no_jwt(self):
        self.setupuser("KujoStar", "14154151451451e4", "kujostar@114.com")
        request = self.factory.post(f"/message/send?username=KujoStar", data={
            "content": "114514"
        }, content_type="application/json")
        response = send(request)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json_response['msg'], "Missing or error type of [authorization]")

    def test_send_messaege_with_invalid_jwt(self):
        self.setupuser("KujoStar", "14154151451451e4", "kujostar@114.com")
        request = self.factory.post(f"/message/send?username=KujoStar", data={
            "content": "114514"
        }, content_type="application/json", HTTP_AUTHORIZATION="Bearer")
        response = send(request)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(json_response['msg'], "Invalid digital signature")

    def test_send_message_with_too_long_content(self):
        self.setupuser("KujoStar", "14154151451451e4", "kujostar@114.com")
        self.setupuser("test", "1415415145111451e4", "test@114.com")
        response = self.send_message("KujoStar", "114514" * 1000, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        self.assertEqual(response.status_code, 413)

    def test_send_message_success(self):
        self.setupuser("KujoStar", "14154151451451e4", "kujostar@114.com")
        self.setupuser("test", "1415415145111451e4", "test@114.com")
        response = self.send_message("KujoStar", "114514", self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        self.assertEqual(response.status_code, 201)
        self.assertTrue("id" in json_response.keys())

    def test_get_record_with_no_jwt(self):
        self.setupuser("KujoStar", "14154151451451e4", "kujostar@114.com")
        self.setupuser("test", "1415415145111451e4", "test@114.com")
        request = self.factory.get(f"/message/record?username=KujoStar", content_type="application/json")
        response = record(request)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json_response['msg'], "Missing or error type of [authorization]")

    def test_get_record_with_invalide_jwt(self):
        self.setupuser("KujoStar", "14154151451451e4", "kujostar@114.com")
        self.setupuser("test", "1415415145111451e4", "test@114.com")
        response = self.get_history("KujoStar", None)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(json_response['msg'], "Invalid digital signature")

    def test_get_record_with_no_target(self):
        self.setupuser("test", "1415415145111451e4", "test@114.com")
        response = self.get_history("KujoStar", self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(json_response['msg'], "User not found")

    def test_get_record_with_self(self):
        self.setupuser("KujoStar", "14154151451451e4", "kujostar@114.com")
        self.setupuser("test", "1415415145111451e4", "test@114.com")
        response = self.get_history("test", self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json_response['result'], [])

    def test_get_record_success(self):
        self.setupuser("KujoStar", "14154151451451e4", "kujostar@114.com")
        self.setupuser("test", "1415415145111451e4", "test@114.com")
        self.send_message("KujoStar", "114514114514", self.jwt)
        response = self.get_history("KujoStar", self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json_response['result'] != [])
        self.assertTrue(json_response['count'] != 0)
