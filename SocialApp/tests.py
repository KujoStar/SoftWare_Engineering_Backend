import random
import uuid
import os
from urllib.request import urlopen, Request
from django.test import RequestFactory, TestCase
from UsersApp.models import User, FollowRelation
from ImagesApp.models import AronaImage
from SocialApp.models import Comment, LikeImageRelation, LikeCommentRelation
from .views import *
from ImagesApp.views import *


class SocialTests(TestCase):
    # Initializer
    def setUp(self) -> None:
        self.factory = RequestFactory()
        User.objects.create(username="test", password="2eafb9f0ce17f5d46a35a3f163155ddd9d6230757cf659abffc2a87ed36bb209", 
                            email="test@sharklasers.com", mail_code="231425", salt="6a38b367-1b4a-4c41-b67c-0015092da16f")
        self.user = User.objects.filter(username="test").first()
        self.jwt = os.getenv("TEST_JWT")
    

    # Utility functions
    def illegalize_jwt(self, jw_token: str) -> str:
        header, payload, signature = jw_token.split(".")
        signature = list(signature)
        rand_index = random.randint(0, len(signature) - 1)
        del signature[rand_index]
        signature = "".join(signature)
        return f"{header}.{payload}.{signature}"
    

    def download_image_by_url(self, url: str, path: str) -> None:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.50'}
        url = Request(url, headers=headers)
        with urlopen(url) as response:
            image = response.read()
        with open(path, "wb") as f:
            f.write(image)


    @CheckPath
    def upload_image_by_path(self, path: str, jw_token: str) -> JsonResponse:
        with open(path, "rb") as f:
            payload = {
                "image": f,
            }
            request = self.factory.post("/image/upload", data=payload, HTTP_AUTHORIZATION=f"Bearer {jw_token}")
            response = upload_image(request)
        return response
    
    
    def post_comment(self, content, belong_to_image_id, reply_to_comment_id, jwt):
        payload = {
            "content": content,
            "belongToImageId": belong_to_image_id,
            "replyToCommentId": reply_to_comment_id
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        request = self.factory.post("/social/comment", data=payload, content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {jwt}")
        response = post_comment(request)
        return response
    

    def get_comment_info(self, id, jwt):
        request = self.factory.get(f"/social/comment/{id}", content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {jwt}")
        response = comment_info(request, id)
        return response
    

    def delete_comment(self, id, jwt):
        request = self.factory.delete(f"/social/comment/{id}", content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {jwt}")
        response = comment_info(request, id)
        return response
    

    def like_image(self, id, jwt):
        request = self.factory.put(f"/social/like/image/{id}", content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {jwt}")
        response = like_image(request, id)
        return response
    

    def like_comment(self, id, jwt):
        request = self.factory.put(f"/social/like/comment/{id}", content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {jwt}")
        response = like_comment(request, id)
        return response
    

    # Test cases
    def test_post_comment(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response1 = self.post_comment("test1", image_id, None, self.jwt)
        json_response1 = json.loads(response1.content.decode("utf-8").replace("'", '"'))
        first_level_comment_id = json_response1['id']

        response2 = self.post_comment("test2", image_id, first_level_comment_id, self.jwt)
        json_response2 = json.loads(response2.content.decode("utf-8").replace("'", '"'))

        # check the response
        self.assertEqual(response1.status_code, 201)
        self.assertEqual(response2.status_code, 201)
        keys = {"msg", "id"}
        self.assertEqual(keys, set(json_response1.keys()))
        self.assertEqual(keys, set(json_response2.keys()))
        image = AronaImage.objects.filter(id=image_id).first()
        self.assertEqual(image.comments, 2)


    def test_post_comment_with_invalid_jwt(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.post_comment("test", image_id, None, self.illegalize_jwt(self.jwt))
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Invalid digital signature"})
        self.assertEqual(response.status_code, 401)


    def test_post_comment_with_no_existing_image(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.post_comment("test", image_id + 1, None, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Image to comment not found"})
        self.assertEqual(response.status_code, 404)


    def test_get_comment_info(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.post_comment("test", image_id, None, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        comment_id = json_response["id"]

        response = self.get_comment_info(comment_id, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        keys = {"msg", "id", "content", "poster", "postTime", "likes", "comments", "belongToImageId", "belongToCommentId", "replyToCommentId", "replyToUser", "isLiked"}
        self.assertEqual(keys, set(json_response.keys()))
        self.assertEqual(response.status_code, 200)


    def test_get_comment_info_with_invalid_jwt(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.post_comment("test", image_id, None, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        comment_id = json_response["id"]

        response = self.get_comment_info(comment_id, self.illegalize_jwt(self.jwt))
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Invalid digital signature"})
        self.assertEqual(response.status_code, 401)


    def test_get_comment_info_with_no_existing_comment(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.post_comment("test", image_id, None, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        comment_id = json_response["id"]

        response = self.get_comment_info(comment_id + 1, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Comment not found"})
        self.assertEqual(response.status_code, 404)


    def test_delete_first_level_comment(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.post_comment("test1", image_id, None, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        first_level_comment_id = json_response['id']
        response = self.post_comment("test2", image_id, first_level_comment_id, self.jwt)

        response = self.delete_comment(first_level_comment_id, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Succeed"})
        self.assertEqual(response.status_code, 200)
        image = AronaImage.objects.filter(id=image_id).first()
        self.assertEqual(image.comments, 0)


    def test_delete_second_level_comment(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.post_comment("test1", image_id, None, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        first_level_comment_id = json_response['id']
        response = self.post_comment("test2", image_id, first_level_comment_id, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        second_level_comment_id = json_response['id']
        response = self.post_comment("test3", image_id, second_level_comment_id, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        last_comment_id = json_response['id']

        response = self.delete_comment(second_level_comment_id, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Succeed"})
        self.assertEqual(response.status_code, 200)
        image = AronaImage.objects.filter(id=image_id).first()
        self.assertEqual(image.comments, 2)
        first_level_comment = Comment.objects.filter(id=first_level_comment_id).first()
        self.assertEqual(first_level_comment.comments, 1)
        last_comment = Comment.objects.filter(id=last_comment_id).first()
        self.assertIsNone(last_comment.reply_to_comment)


    def test_delete_comment_with_invalid_jwt(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.post_comment("test", image_id, None, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        comment_id = json_response["id"]

        response = self.delete_comment(comment_id, self.illegalize_jwt(self.jwt))
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Invalid digital signature"})
        self.assertEqual(response.status_code, 401)


    def test_delete_comment_with_no_existing_comment(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.post_comment("test", image_id, None, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        comment_id = json_response["id"]

        response = self.delete_comment(comment_id + 1, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Comment not found"})
        self.assertEqual(response.status_code, 404)


    def test_delete_comment_posted_by_others(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.post_comment("test", image_id, None, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        comment_id = json_response["id"]

        comment = Comment.objects.filter(id=comment_id).first()
        User.objects.create(username="test2", password="test2", email="test2", mail_code="test2", salt="test2")
        comment.poster = User.objects.exclude(username="test").first()
        comment.save()

        response = self.delete_comment(comment_id, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "You are not the poster of this comment"})
        self.assertEqual(response.status_code, 403)


    def test_like_image(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.like_image(image_id, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Succeed"})
        self.assertEqual(response.status_code, 200)
        image = AronaImage.objects.filter(id=image_id).first()
        self.assertEqual(image.likes, 1)

    
    def test_unlike_image(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.like_image(image_id, self.jwt)
        response = self.like_image(image_id, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Succeed"})
        self.assertEqual(response.status_code, 200)
        image = AronaImage.objects.filter(id=image_id).first()
        self.assertEqual(image.likes, 0)


    def test_like_image_with_invalid_jwt(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.like_image(image_id, self.illegalize_jwt(self.jwt))
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Invalid digital signature"})
        self.assertEqual(response.status_code, 401)


    def test_like_image_not_existing(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.like_image(image_id + 1, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Image not found"})
        self.assertEqual(response.status_code, 404)


    def test_like_comment(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.post_comment("test", image_id, None, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        comment_id = json_response["id"]

        response = self.like_comment(comment_id, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Succeed"})
        self.assertEqual(response.status_code, 200)
        comment = Comment.objects.filter(id=comment_id).first()
        self.assertEqual(comment.likes, 1)
        

    def test_unlike_comment(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.post_comment("test", image_id, None, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        comment_id = json_response["id"]

        response = self.like_comment(comment_id, self.jwt)
        response = self.like_comment(comment_id, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Succeed"})
        self.assertEqual(response.status_code, 200)
        comment = Comment.objects.filter(id=comment_id).first()
        self.assertEqual(comment.likes, 0)


    def test_like_comment_with_invalid_jwt(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.post_comment("test", image_id, None, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        comment_id = json_response["id"]

        response = self.like_comment(comment_id, self.illegalize_jwt(self.jwt))
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Invalid digital signature"})
        self.assertEqual(response.status_code, 401)


    def test_like_comment_not_existing(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.post_comment("test", image_id, None, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        comment_id = json_response["id"]

        response = self.like_comment(comment_id + 1, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Comment not found"})
        self.assertEqual(response.status_code, 404)