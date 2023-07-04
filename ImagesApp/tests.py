import random
import uuid
from PIL import Image
from urllib.request import urlopen, Request
from django.test import RequestFactory, Client, TestCase
from ImagesApp.models import AronaImage
from SocialApp.models import Comment
from UsersApp.models import User
from ImagesApp.config import *
from .views import *
from SocialApp.views import *


class ImagesTests(TestCase):
    # Initializer
    def setUp(self) -> None:
        self.path = TMP_DIR
        self.factory = RequestFactory()
        User.objects.create(username="test", password="2eafb9f0ce17f5d46a35a3f163155ddd9d6230757cf659abffc2a87ed36bb209", 
                            email="test@sharklasers.com", mail_code="231425", salt="6a38b367-1b4a-4c41-b67c-0015092da16f")
        self.user = User.objects.filter(username="test").first()
        self.jwt = os.getenv("TEST_JWT")

        if not os.path.exists(self.path):
            os.mkdir(self.path)

    
    # Utility functions
    def illegalize_jwt(self, jw_token: str) -> str:
        header, payload, signature = jw_token.split(".")
        signature = list(signature)
        rand_index = random.randint(0, len(signature) - 1)
        del signature[rand_index]
        signature = "".join(signature)
        return f"{header}.{payload}.{signature}"
    

    def illegalize_hash(self, hash: str) -> str:
        hash = list(hash)
        rand_index = random.randint(0, len(hash) - 1)
        del hash[rand_index]
        hash = "".join(hash)
        return hash
    

    @CheckPath
    def upload_image_by_path(self, filename: str, jw_token: str) -> JsonResponse:
        with open(filename, "rb") as f:
            payload = {
                "image": f,
            }
            request = self.factory.post("/image/upload", data=payload, HTTP_AUTHORIZATION=f"Bearer {jw_token}")
            response = upload_image(request)
        return response
    

    def get_image_info(self, id, jwt):
        request = self.factory.get(f"/image/{id}", content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {jwt}")  
        response = image_info(request, id)
        return response
    

    def change_image_info(self, id, title, tags, description, category, jwt):
        payload = {
            "title": title,
            "tags": tags,
            "description": description,
            "category": category
        }
        request = self.factory.patch(f"/image/{id}", data=payload, content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {jwt}")
        response = image_info(request, id)
        return response
    

    def delete_image(self, id, jwt):
        request = self.factory.delete(f"/image/{id}", content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {jwt}")
        response = image_info(request, id)
        return response
    
    
    def get_image_comment_info(self, id, jwt):
        request = self.factory.get(f"/image/{id}/comments", content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {jwt}")
        response = image_comments(request, id)
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


    def delete_comment(self, id, jwt):
        request = self.factory.delete(f"/social/comment/{id}", content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {jwt}")
        response = comment_info(request, id)
        return response


    @CheckPath
    def download_image_by_url(self, url: str, filename: str) -> None:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.50'}
        url = Request(url, headers=headers)
        with urlopen(url) as response:
            image = response.read()
        with open(filename, "wb") as f:
            f.write(image)
    

    @CheckPath
    def upload_empty_image(self, jw_token: str) -> JsonResponse:
        request = self.factory.post("/image/upload", HTTP_AUTHORIZATION=f"Bearer {jw_token}")
        response = upload_image(request)
        return response
    

    def get_image_info_by_id(self, id: int, jw_token: str=None) -> JsonResponse:
        if jw_token is None:
            request = self.factory.get(f"/image/{id}")
        else:
            request = self.factory.get(f"/image/{id}", HTTP_AUTHORIZATION=f"Bearer {jw_token}")
        response = image_info(request, id)
        return response
    

    @CheckPath
    def get_raw_image_by_hash(self, hash: str) -> HttpResponse:
        request = self.factory.get(f"/image/raw/{hash}")
        response = image(request, hash)
        return response
    

    @CheckPath
    def get_rough_image_by_hash(self, hash: str) -> HttpResponse:
        request = self.factory.get(f"/image/rough/{hash}")
        response = rough_image(request, hash)
        return response
    

    def delete_image_by_id(self, id: int, jw_token: str) -> JsonResponse:
        request = self.factory.delete(f"/image/{id}", HTTP_AUTHORIZATION=f"Bearer {jw_token}")
        response = image_info(request, id)
        return response
    

    # Test cases
    def test_semiupload_with_no_existing_image(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        image_hash = AronaImage.objects.filter(id=image_id).first().hash

        payload = {
            "hash": self.illegalize_hash(image_hash),
        }
        request = self.factory.post("/image/semiupload", data=payload, content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {self.jwt}")
        response = semiupload(request)
        
        # check the response
        self.assertEqual(response.status_code, 204)


    def test_semiupload_with_existing_image(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        image_hash = AronaImage.objects.filter(id=image_id).first().hash
        
        payload = {
            "hash": image_hash,
        }
        request = self.factory.post("/image/semiupload", data=payload, content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {self.jwt}")
        response = semiupload(request)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        
        # check the response
        self.assertEqual(response.status_code, 200)


    def test_semiupload_with_invalid_jwt(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        image_hash = AronaImage.objects.filter(id=image_id).first().hash

        payload = {
            "hash": image_hash,
        }
        request = self.factory.post("/image/semiupload", data=payload, content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {self.illegalize_jwt(self.jwt)}")
        response = semiupload(request)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        
        # check the response
        self.assertEqual(response.status_code, 401)
        self.assertEqual(json_response, {"msg": "Invalid digital signature"})


    def test_upload_image_gif(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Succeed", "id": json_response["id"]})
        image_id = json_response["id"]
        self.assertEqual(response.status_code, 201)
        self.assertTrue(AronaImage.objects.filter(id=image_id).exists())
        image_hash = AronaImage.objects.filter(id=image_id).first().hash
        gif_name = str(uuid.uuid4()) + ".gif"
        self.assertIsNone(fget_object(gif_name, "gif", image_hash))
        self.assertIsNone(fget_object(gif_name, "gif", image_hash, rough=True))


    def test_upload_image_gif_with_invalid_jwt(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.illegalize_jwt(self.jwt))
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Invalid digital signature"})
        self.assertEqual(response.status_code, 401)


    def test_upload_image_jpeg(self):
        url = "https://i.imgloc.com/2023/05/24/VDwXqU.jpeg"
        change_to_tmp_dir()
        jpeg_name = str(uuid.uuid4()) + ".jpeg"
        self.download_image_by_url(url, jpeg_name)
        response = self.upload_image_by_path(jpeg_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Succeed", "id": json_response["id"]})
        image_id = json_response["id"]
        self.assertEqual(response.status_code, 201)
        self.assertTrue(AronaImage.objects.filter(id=image_id).exists())
        image_hash = AronaImage.objects.filter(id=image_id).first().hash
        jpeg_name = str(uuid.uuid4()) + ".jpeg"
        self.assertIsNone(fget_object(jpeg_name, "jpeg", image_hash))
        self.assertIsNone(fget_object(jpeg_name, "jpeg", image_hash, rough=True))


    def test_upload_image_png(self):
        url = "https://i.imgloc.com/2023/05/24/VDwBGp.png"
        change_to_tmp_dir()
        png_name = str(uuid.uuid4()) + ".png"
        self.download_image_by_url(url, png_name)
        response = self.upload_image_by_path(png_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Succeed", "id": json_response["id"]})
        image_id = json_response["id"]
        self.assertEqual(response.status_code, 201)
        self.assertTrue(AronaImage.objects.filter(id=image_id).exists())
        image_hash = AronaImage.objects.filter(id=image_id).first().hash
        png_name = str(uuid.uuid4()) + ".png"
        self.assertIsNone(fget_object(png_name, "png", image_hash))
        self.assertIsNone(fget_object(png_name, "png", image_hash, rough=True))


    def test_upload_empty_image(self):
        response = self.upload_empty_image(self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Missing image"})
        self.assertEqual(response.status_code, 400)


    def test_image_categories(self):
        request = self.factory.get("/image/category")
        response = image_category(request)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        expected_keys = {"msg", "categories"}
        self.assertTrue(expected_keys == set(json_response.keys()))
        self.assertEqual(response.status_code, 200)


    def test_get_image_info(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.get_image_info_by_id(image_id, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        expected_keys = {"msg", "id", "hash", "contentType", "uploader", "uploadTime", "likes", "comments", "width", "height", "title", "tags", "description", "category", "isLiked"}
        self.assertTrue(expected_keys == set(json_response.keys()))
        self.assertEqual(response.status_code, 200)


    def test_get_image_info_without_jwt(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.get_image_info_by_id(image_id)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        expected_keys = {"msg", "id", "hash", "contentType", "uploader", "uploadTime", "likes", "comments", "width", "height", "title", "tags", "description", "category", "isLiked"}
        self.assertTrue(expected_keys == set(json_response.keys()))
        self.assertEqual(response.status_code, 200)


    def test_get_image_info_with_invalid_jwt(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.get_image_info_by_id(image_id, self.illegalize_jwt(self.jwt))
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Invalid digital signature"})
        self.assertEqual(response.status_code, 401)


    def test_get_image_info_with_invalid_id(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.get_image_info_by_id(image_id + 1, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Image not found"})
        self.assertEqual(response.status_code, 404)


    def test_change_image_info(self):
        title = "testimage"
        tags = ["test", "image"]
        description = "test for image"
        category = "meme"

        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)

        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]
        
        response = self.change_image_info(image_id, title, tags, description, category, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Succeed"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AronaImage.objects.filter(id=image_id, title=title, tags=tags, description=description, category=category).exists())


    def test_change_image_info_with_invalid_jwt(self):
        title = "testimage"
        tags = ["test", "image"]
        description = "test for image"
        category = "meme"

        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)

        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]
        
        response = self.change_image_info(image_id, title, tags, description, category, self.illegalize_jwt(self.jwt))
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Invalid digital signature"})
        self.assertEqual(response.status_code, 401)


    def test_change_image_info_with_invalid_id(self):
        title = "testimage"
        tags = ["test", "image"]
        description = "test for image"
        category = "meme"

        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)

        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.change_image_info(image_id + 1, title, tags, description, category, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Image not found"})
        self.assertEqual(response.status_code, 404)


    def test_change_image_info_with_invalid_category(self):
        title = "testimage"
        tags = ["test", "image"]
        description = "test for image"
        category = "abracadabra"

        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)

        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        response = self.change_image_info(image_id, title, tags, description, category, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Invalid category"})
        self.assertEqual(response.status_code, 400)


    def test_change_image_info_uploaded_by_others(self):
        title = "testimage"
        tags = ["test", "image"]
        description = "test for image"
        category = "abracadabra"

        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)

        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        image = AronaImage.objects.filter(id=image_id).first()
        User.objects.create(username="test2", password="test2", email="test2", mail_code="test2", salt="test2")
        image.uploader = User.objects.exclude(username="test").first()
        image.save()

        response = self.change_image_info(image_id, title, tags, description, category, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "You are not the uploader of this image"})
        self.assertEqual(response.status_code, 403)

    
    def test_delete_image(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)

        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        image_id = json_response["id"]
        response = self.delete_image_by_id(image_id, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Succeed"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AronaImage.objects.filter(id=image_id).exists())


    def test_delete_image_with_invalid_jwt(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode("utf-8").replace("'", "'"))

        image_id = json_response["id"]
        response = self.delete_image_by_id(image_id, self.illegalize_jwt(self.jwt))
        json_response = json.loads(response.content.decode("utf-8").replace("'", "'"))

        # check the response
        self.assertEqual(json_response, {"msg": "Invalid digital signature"})
        self.assertEqual(response.status_code, 401)


    def test_delete_image_with_invalid_id(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode("utf-8").replace("'", "'"))

        image_id = json_response["id"]
        response = self.delete_image_by_id(image_id + 1, self.jwt)
        json_response = json.loads(response.content.decode("utf-8").replace("'", "'"))

        # check the response
        self.assertEqual(json_response, {"msg": "Image not found"})
        self.assertEqual(response.status_code, 404)


    def test_delete_image_uploaded_by_others(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode("utf-8").replace("'", "'"))

        image_id = json_response["id"]
        image = AronaImage.objects.filter(id=image_id).first()
        User.objects.create(username="test2", password="test2", email="test2", mail_code="test2", salt="test2")
        image.uploader = User.objects.exclude(username="test").first()
        image.save()

        response = self.delete_image_by_id(image_id, self.jwt)
        json_response = json.loads(response.content.decode("utf-8").replace("'", "'"))

        # check the response
        self.assertEqual(json_response, {"msg": "You are not the uploader of this image"})
        self.assertEqual(response.status_code, 403)


    def test_image_by_gif(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        # get the image hash
        image_hash = AronaImage.objects.filter(id=image_id).first().hash

        # query the image
        response = self.get_raw_image_by_hash(image_hash)

        # check the response
        self.assertEqual(response.status_code, 200)


    def test_image_by_jpeg(self):
        url = "https://i.imgloc.com/2023/05/24/VDwXqU.jpeg"
        change_to_tmp_dir()
        jpeg_name = str(uuid.uuid4()) + ".jpeg"
        self.download_image_by_url(url, jpeg_name)
        response = self.upload_image_by_path(jpeg_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        # get the image hash
        image_hash = AronaImage.objects.filter(id=image_id).first().hash

        # query the image
        response = self.get_raw_image_by_hash(image_hash)

        # check the response
        self.assertEqual(response.status_code, 200)


    def test_image_by_png(self):
        url = "https://i.imgloc.com/2023/05/24/VDwBGp.png"
        change_to_tmp_dir()
        png_name = str(uuid.uuid4()) + ".png"
        self.download_image_by_url(url, png_name)
        response = self.upload_image_by_path(png_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        # get the image hash
        image_hash = AronaImage.objects.filter(id=image_id).first().hash

        # query the image
        response = self.get_raw_image_by_hash(image_hash)

        # check the response
        self.assertEqual(response.status_code, 200)


    def test_image_with_invalid_hash(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        # get the image hash
        image_hash = AronaImage.objects.filter(id=image_id).first().hash

        # query the image
        request = self.factory.get(f"/image/raw/{self.illegalize_hash(image_hash)}")
        response = image(request, self.illegalize_hash(image_hash))
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Image not found"})
        self.assertEqual(response.status_code, 404)


    def test_rough_image_by_gif(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)

        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        # get the image hash
        image_hash = AronaImage.objects.filter(id=image_id).first().hash

        # query the image
        response = self.get_rough_image_by_hash(image_hash)

        # check the response
        self.assertEqual(response.status_code, 200)


    def test_rough_image_by_jpeg(self):
        url = "https://i.imgloc.com/2023/05/24/VDwXqU.jpeg"
        change_to_tmp_dir()
        jpeg_name = str(uuid.uuid4()) + ".jpeg"
        self.download_image_by_url(url, jpeg_name)
        response = self.upload_image_by_path(jpeg_name, self.jwt)

        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        # get the image hash
        image_hash = AronaImage.objects.filter(id=image_id).first().hash

        # query the image
        response = self.get_rough_image_by_hash(image_hash)

        # check the response
        self.assertEqual(response.status_code, 200)


    def test_rough_image_by_png(self):
        url = "https://i.imgloc.com/2023/05/24/VDwBGp.png"
        change_to_tmp_dir()
        png_name = str(uuid.uuid4()) + ".png"
        self.download_image_by_url(url, png_name)
        response = self.upload_image_by_path(png_name, self.jwt)

        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        # get the image hash
        image_hash = AronaImage.objects.filter(id=image_id).first().hash

        # query the image
        response = self.get_rough_image_by_hash(image_hash)

        # check the response
        self.assertEqual(response.status_code, 200)


    def test_rough_image_with_invalid_hash(self):
        url = "https://i.imgloc.com/2023/05/24/VDw3ca.gif"
        change_to_tmp_dir()
        gif_name = str(uuid.uuid4()) + ".gif"
        self.download_image_by_url(url, gif_name)
        response = self.upload_image_by_path(gif_name, self.jwt)

        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))
        image_id = json_response["id"]

        # get the image hash
        image_hash = AronaImage.objects.filter(id=image_id).first().hash

        # query the image
        request = self.factory.get(f"/image/rough/{self.illegalize_hash(image_hash)}")
        response = rough_image(request, self.illegalize_hash(image_hash))
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Image not found"})
        self.assertEqual(response.status_code, 404)

    
    def test_get_image_comments(self):
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

        response = self.get_image_comment_info(image_id, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response['msg'], "Succeed")
        self.assertEqual(response.status_code, 200)
        origin_keys = {"msg", "count", "perPage", "result"}
        keys = {"id", "content", "poster", "postTime", "likes", "comments", "isLiked", "replies"}
        reply_keys = {"id", "content", "poster", "postTime", "likes", "replyToUser", "isLiked"}
        self.assertEqual(origin_keys, set(json_response.keys()))
        self.assertEqual(keys, set(json_response['result'][0].keys()))
        self.assertEqual(len(json_response['result']), 1)
        self.assertEqual(reply_keys, set(json_response['result'][0]['replies'][0].keys()))
        self.assertEqual(len(json_response['result'][0]['replies']), 1)


    def test_get_image_comments_with_invalid_jwt(self):
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

        response = self.get_image_comment_info(image_id, self.illegalize_jwt(self.jwt))
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Invalid digital signature"})
        self.assertEqual(response.status_code, 401)
    
    def test_get_image_comments_with_invalid_id(self):
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

        response = self.get_image_comment_info(image_id + 1, self.jwt)
        json_response = json.loads(response.content.decode(response.charset).replace("'", '"'))

        # check the response
        self.assertEqual(json_response, {"msg": "Image not found"})
        self.assertEqual(response.status_code, 404)