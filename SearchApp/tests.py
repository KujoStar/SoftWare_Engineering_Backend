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
class SearchTests(TestCase):
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
    
    def search_image_with_no_jwt(self, searchFor):
        request = self.factory.get(f"/search/images?searchFor={searchFor}", content_type="application/json")
        response = search_image(request)
        return response
    
    def search_image_with_jwt(self, searchFor, jwt):
        request = self.factory.get(f"/search/images?searchFor={searchFor}", content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {jwt}")
        response = search_image(request)
        return response
    
    def search_image_with_pageid(self, searchFor, pageid):
        request = self.factory.get(f"/search/images?searchFor={searchFor}&pageId={pageid}", content_type="application/json")
        response = search_image(request)
        return response
    
    def search_image_with_sortedBy(self, searchFor, sortedBy):
        request = self.factory.get(f"/search/images?searchFor={searchFor}&sortedBy={sortedBy}", content_type="application/json")
        response = search_image(request)
        return response
    
    def search_image_with_regexp(self, searchFor):
        request = self.factory.get(f"/search/images?searchFor={searchFor}&regexp=1", content_type="application/json")
        response = search_image(request)
        return response
    
    def get_search_history(self, jwt):
        request = self.factory.get(f"/search/history", content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {jwt}")
        response = search_history(request)
        return response
    
    def get_search_history_without_jwt(self):
        request = self.factory.get(f"/search/history", content_type="application/json")
        response = search_history(request)
        return response
    
    def search_user_with_jwt(self, content, jwt):
        request = self.factory.get(f"/search/user?content={content}", content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {jwt}")
        response = search_user(request)
        return response
    
    def test_search_image(self):
        response = self.search_image_with_no_jwt(" ")
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        self.assertEqual(response.status_code, 200)
        # expected_key = {"id", "hash", "contentType", "uploader", "uploadTime", "likes", "comments", "width", "height", "title", "tags", "description", "category", "isLiked"}
        self.assertEqual(json_response['result'], [])

    def test_search_image_with_page_id(self):
        response = self.search_image_with_pageid(" ", 1000)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

    def test_search_image_with_sort_by(self):
        response = self.search_image_with_sortedBy(" ", "uploadTime")
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        self.assertEqual(response.status_code, 200)

    def test_search_image_with_regexp(self):
        response = self.search_image_with_regexp(".*")
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        self.assertEqual(response.status_code, 200)
        # expected_key = {"id", "hash", "contentType", "uploader", "uploadTime", "likes", "comments", "width", "height", "title", "tags", "description", "category", "isLiked"}
        self.assertEqual(json_response['result'], [])

    def test_search_with_invalid_method(self):
        request = self.factory.post(f"/search/images?searchFor=miku", content_type="application/json")
        response = search_image(request)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(json_response['msg'], "Bad method")

    def test_get_search_history(self):
        self.setupuser("test", "wjdyhswdwdwdwd", "114514@test.com")
        self.search_image_with_jwt("miku", self.jwt)
        response = self.get_search_history(self.jwt)
        self.assertEqual(response.status_code, 200)

    def test_get_search_history_with_invalid_method(self):
        request = self.factory.post("/search/history", content_type="application/json")
        response = search_image(request)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(json_response['msg'], "Bad method")

    def test_get_search_history_without_jwt(self):
        response = self.get_search_history_without_jwt()
        self.assertEqual(response.status_code, 400)

    def test_search_user_nothing(self):
        response = self.search_user_with_jwt("", self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json_response['result'], [])

    def test_search_user_success(self):
        self.setupuser("test", "114114114114114", "test@114.com")
        self.setupuser("miku", "mikumikumikukawaii", "miku@kawaii.com")
        response = self.search_user_with_jwt("miku", self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(json_response['result'])

    def test_search_user_with_invalid_method(self):
        request = self.factory.post("/search/user?content=miku", content_type="application/json")
        response = search_image(request)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(json_response['msg'], "Bad method")