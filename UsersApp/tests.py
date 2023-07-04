from django.test import TestCase
from UsersApp.models import User, FollowRelation
from ImagesApp.models import AronaImage
import random as rd
import os
from blake3 import blake3
# Create your tests here.
class UsersTests(TestCase):
    def setUp(self):
        self.jwt = os.getenv("TEST_JWT")
        
    def setupuser(self, username, password, email):
        if not User.objects.filter(username = username).exists():
            user = User(username = username, password = password, email = email)
            user.save()
    
    def preregister(self, username, email):
        payload = {
            "username": username,
            "email": email
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        return self.client.post("/preregister", data=payload, content_type="application/json")
    
    def register(self, password, salt, code):
        payload = {
            "password": password,
            "salt": salt,
            "code": code
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        return self.client.post("/register", data=payload, content_type="application/json")
    
    def prelogin(self, username):
        payload = {
            "username": username
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        return self.client.post("/prelogin", data=payload, content_type="application/json")
    
    def login(self, username, password):
        payload = {
            "username": username,
            "password": password
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        return self.client.post("/login", data=payload, content_type="application/json")

    def get_user_info(self, username):
        return self.client.get(f"/user/{username}", content_type="application/json")
    
    def get_user_detail_info(self, username, jwt):
        return self.client.get(f"/user/{username}/detail", HTTP_AUTHORIZATION=f"Bearer {jwt}", content_type="application/json")
    
    def change_user_info(self, username, nickname, slogan, jwt):
        payload = {
            "nickname": nickname,
            "slogan": slogan
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        
        return self.client.put(f"/user/{username}", data=payload, HTTP_AUTHORIZATION=f"Bearer {jwt}", content_type="application/json")
    
    def follow_user(self, username, jwt):
        return self.client.post(f"/user/{username}/follow", HTTP_AUTHORIZATION=f"Bearer {jwt}",content_type="application/json")
    
    def unfollow_user(self, username, jwt):
        return self.client.post(f"/user/{username}/unfollow", HTTP_AUTHORIZATION=f"Bearer {jwt}",content_type="application/json")
    
    def get_user_follower(self, username):
        return self.client.get(f"/user/{username}/follower",content_type="application/json")
    
    def get_user_following(self, username):
        return self.client.get(f"/user/{username}/following",content_type="application/json")
    
    def get_user_image(self, username):
        return self.client.get(f"/user/{username}/images",content_type="application/json")
    '''
    def test_preregister_success(self):
        res = self.preregister("KujoStar", "2322751077@qq.com")
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Succeed")
        self.assertIsNotNone(json_response['salt'])
        self.assertEqual(res.status_code, 200)
    '''
    def test_preregister_with_no_username(self):
        res = self.preregister(None, "12wed@114.com")
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Missing or error type of [username]")
        self.assertEqual(res.status_code, 400)

    def test_preregister_with_no_email(self):
        res = self.preregister("ttest", None)
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Missing or error type of [email]")
        self.assertEqual(res.status_code, 400)

    def test_preregister_with_other_method(self):
        res = self.client.put("/preregister", data={
            "username": "test11111",
            "email": "1wedwjhscgj@114.com"
        }, content_type="application/json")
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Bad method")
        self.assertEqual(res.status_code, 405)

    def test_preregister_with_exist_username(self):
        self.setupuser("test1", "1234567890qaz", "1234567@114.com")
        res = self.preregister("test1", "12345677@114.com")
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Username has been registed")
        self.assertEqual(res.status_code, 400)

    def test_preregister_with_exist_email(self):
        self.setupuser("test2", "12348727itw", "2322751077@qq.com")
        res = self.preregister("test3", "2322751077@qq.com")
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Email has been used")
        self.assertEqual(res.status_code, 400)

    def test_register_with_no_password(self):
        res = self.register(None, "123456ceqsx", "114514")
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Missing or error type of [password]")
        self.assertEqual(res.status_code, 400)

    def test_register_with_no_salt(self):
        res = self.register("tessst", None, "114514")
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Missing or error type of [salt]")
        self.assertEqual(res.status_code, 400)

    def test_register_with_no_code(self):
        res = self.register("tessssst", "123456ceqsx", None)
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Missing or error type of [code]")
        self.assertEqual(res.status_code, 400)

    def test_register_with_other_method(self):
        res = self.client.put("/register", data={
            "password": "12wedfv",
            "salt": "temsor1234",
            "code": "114514"
        }, content_type="application/json")
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Bad method")
        self.assertEqual(res.status_code, 405)

    def test_register_with_invalid_salt(self):
        res = self.register("1ihtftwe", "1sbhhiqiug", "114514")
        json_response = res.json()
        self.assertEqual(json_response['msg'], "uuid not found")
        self.assertEqual(res.status_code, 404)

    def test_prelogin_with_no_username(self):
        res = self.prelogin(None)
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Missing or error type of [username]")
        self.assertEqual(res.status_code, 400)

    def test_prelogin_with_other_method(self):
        res = self.client.put("/prelogin", data={
            "username": "tttt112"
        }, content_type="application/json")
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Bad method")
        self.assertEqual(res.status_code, 405)

    def test_prelogin_with_invalid_name(self):
        res = self.prelogin("test176")
        json_response = res.json()
        self.assertEqual(json_response['msg'], "User not found")
        self.assertEqual(res.status_code, 404)

    def test_login_with_no_username(self):
        res = self.login(None, "1sasdw1sw")
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Missing or error type of [username]")
        self.assertEqual(res.status_code, 400)

    def test_login_with_no_password(self):
        res = self.login("test1hg", None)
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Missing or error type of [password]")
        self.assertEqual(res.status_code, 400)

    def test_login_with_other_method(self):
        res = self.client.put("/login", data={
            "username": "tesstftgy",
            "password": "1swfrgtgrrg"
        }, content_type="application/json")
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Bad method")
        self.assertEqual(res.status_code, 405)

    def test_login_with_invalid_name(self):
        res = self.login("test198", "1qwrbija")
        json_response = res.json()
        self.assertEqual(json_response['msg'], "User not found")
        self.assertEqual(res.status_code, 404)

    def test_login_with_incorrect_password(self):
        origin_password = "1gxvkhti72d3"
        blake3hash_password = blake3(origin_password.encode()).hexdigest()
        self.setupuser("test514", blake3hash_password, "232278@114.com")
        res = self.login("test514", "1234567890")
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Password incorrect")
        self.assertEqual(res.status_code, 400)

    def test_login_success(self):
        origin_password = "qazwsxedc"
        blake3hash_password = blake3(origin_password.encode()).hexdigest()
        self.setupuser("test114514", blake3hash_password, "232278@114.com")
        res = self.login("test114514", "qazwsxedc")
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Succeed")
        self.assertEqual(json_response['username'], "test114514")
        self.assertIsNotNone(json_response['jwt'])
        self.assertEqual(res.status_code, 200)

    def test_get_user_info_with_no_name(self):
        res = self.get_user_info(None)
        json_response = res.json()
        self.assertEqual(json_response['msg'], "user not found")
        self.assertEqual(res.status_code, 404)

    def test_get_user_info_with_other_method(self):
        self.setupuser("test12345", "iuzugcidbi", "1323rdjhg@114.com")
        res = self.client.patch("/user/test12345", content_type="application/json")
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Bad method")
        self.assertEqual(res.status_code, 405)

    def test_get_user_info_success(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        res = self.get_user_info("KujoStar")
        self.assertEqual(res.json()['msg'], "Succeed")
        self.assertEqual(res.status_code, 200)
        
    def test_get_user_info_fail(self):
        res = self.get_user_info("DioBrando")
        self.assertEqual(res.json()['msg'], "user not found")
        self.assertEqual(res.status_code, 404)
        
    def test_get_user_detail_info_success(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        res = self.get_user_detail_info("KujoStar", self.jwt)
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Succeed")
        self.assertEqual(res.status_code, 200)
        
    def test_get_user_detail_info_fail(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        res = self.get_user_detail_info("DioBrando", self.jwt)
        json_response = res.json()
        self.assertEqual(json_response['msg'], "user not found")
        self.assertEqual(res.status_code, 404)

    def test_follow_with_no_jwt(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        res = self.client.post("/user/KujoStar/follow", content_type="application/json")
        json_response = res.json()
        self.assertEqual(json_response["msg"], "You haven't logged in yet.")
        self.assertEqual(res.status_code, 400)

    def test_follow_success(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        res = self.follow_user("KujoStar", self.jwt)
        json_response = res.json()
        self.assertEqual(res.status_code, 200)
         
    def test_follow_not_exist_user(self):
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        res = self.follow_user("DioBrando", self.jwt)
        self.assertEqual(res.status_code, 404)
        
    def test_follow_self(self):
        self.setupuser("test", "123435672435", "114514@qq.com")
        res = self.follow_user("test", self.jwt)
        self.assertEqual(res.status_code, 400)
        
    def test_follow_user_twice(self):
        self.setupuser("Jotaro", "114qwergfh919810", "dsafs@qq.com")
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        self.follow_user("Jotaro", self.jwt)
        res = self.follow_user("Jotaro", self.jwt)
        self.assertEqual(res.status_code, 400)
    
    def test_unfollow_with_no_jwt(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        res = self.client.post("/user/KujoStar/unfollow", content_type="application/json")
        json_response = res.json()
        self.assertEqual(json_response["msg"], "You haven't logged in yet.")
        self.assertEqual(res.status_code, 400)

    def test_unfollow_user(self):
        self.setupuser("DioBrando", "114514qef0", "1324567@qq.com")
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        self.follow_user("DioBrando", self.jwt)
        res = self.unfollow_user("DioBrando", self.jwt)
        json_response = res.json()
        self.assertEqual(res.status_code, 200)
     
    def test_unfollow_self(self):
        self.setupuser("test", "123435672435", "114514@qq.com")
        res = self.unfollow_user("test", self.jwt)
        self.assertEqual(res.status_code, 400)
        
    def test_unfollow_user_not_exist(self):
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        res = self.unfollow_user("Diosama", self.jwt)
        self.assertEqual(res.status_code, 404)
        
    def test_unfollow_user_twice(self):
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        self.setupuser("Kujo1", "1145adsfxv9810", "2327510277@qq.com")
        self.follow_user("Kujo1", self.jwt)
        self.unfollow_user("Kujo1", self.jwt)
        res = self.unfollow_user("Kujo1", self.jwt)
        self.assertEqual(res.status_code, 404)

    def test_get_user_follower_success(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        self.follow_user("KujoStar", self.jwt)
        res = self.get_user_follower("KujoStar")
        json_response = res.json()
        self.assertEqual(res.status_code, 200)
        self.assertEqual("test" in json_response["followers"], True)

    def test_get_follower_success_with_params(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        self.follow_user("KujoStar", self.jwt)
        res = self.client.get("/user/KujoStar/follower?pageSize=20&pageId=1", content_type="application/json")
        json_response = res.json()
        self.assertEqual(res.status_code, 200)
        self.assertEqual("test" in json_response["followers"], True)

    def test_get_follower_success_with_too_large_params(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        self.follow_user("KujoStar", self.jwt)
        res = self.client.get("/user/KujoStar/follower?pageSize=20&pageId=2", content_type="application/json")
        json_response = res.json()
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(json_response['followers']) == 0)

    def test_get_follower_empty(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        res = self.client.get("/user/KujoStar/follower?pageSize=20&pageId=1", content_type="application/json")
        json_response = res.json()
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(json_response['followers']) == 0)

    def test_get_follower_with_invalid_param(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        self.follow_user("KujoStar", self.jwt)
        res = self.client.get("/user/KujoStar/follower?pagestart=20", content_type="application/json")
        json_response = res.json()
        self.assertEqual(res.status_code, 400)
        self.assertEqual(json_response['msg'], "Invalid params")

    def test_get_follower_with_invalid_param_type_1(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        self.follow_user("KujoStar", self.jwt)
        res = self.client.get("/user/KujoStar/follower?pageSize=qq", content_type="application/json")
        json_response = res.json()
        self.assertEqual(res.status_code, 400)
        self.assertEqual(json_response['msg'], "Invalid params [pageSize]")

    def test_get_follower_with_invalid_param_type_2(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        self.follow_user("KujoStar", self.jwt)
        res = self.client.get("/user/KujoStar/follower?pageId=qq", content_type="application/json")
        json_response = res.json()
        self.assertEqual(res.status_code, 400)
        self.assertEqual(json_response['msg'], "Invalid params [pageId]")

    def test_get_user_following_success(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        self.follow_user("KujoStar", self.jwt)
        res = self.get_user_following("test")
        json_response = res.json()
        self.assertEqual(res.status_code, 200)
        self.assertEqual("KujoStar" in json_response["followings"], True)

    def test_get_following_success_with_params(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        self.follow_user("KujoStar", self.jwt)
        res = self.client.get("/user/test/following?pageSize=20&pageId=1", content_type="application/json")
        json_response = res.json()
        self.assertEqual(res.status_code, 200)
        self.assertEqual("KujoStar" in json_response["followings"], True)

    def test_get_following_success_with_too_large_params(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        self.follow_user("KujoStar", self.jwt)
        res = self.client.get("/user/test/following?pageSize=20&pageId=2", content_type="application/json")
        json_response = res.json()
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(json_response['followings']) == 0)

    def test_get_following_empty(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        res = self.client.get("/user/KujoStar/following?pageSize=20&pageId=1", content_type="application/json")
        json_response = res.json()
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(json_response['followings']) == 0)

    def test_get_following_with_invalid_param(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        self.follow_user("KujoStar", self.jwt)
        res = self.client.get("/user/test/following?pagestart=20", content_type="application/json")
        json_response = res.json()
        self.assertEqual(res.status_code, 400)
        self.assertEqual(json_response['msg'], "Invalid params")

    def test_get_following_with_invalid_param_type_1(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        self.follow_user("KujoStar", self.jwt)
        res = self.client.get("/user/test/following?pageSize=qq", content_type="application/json")
        json_response = res.json()
        self.assertEqual(res.status_code, 400)
        self.assertEqual(json_response['msg'], "Invalid params [pageSize]")

    def test_get_following_with_invalid_param_type_2(self):
        self.setupuser("KujoStar", "1145141919810", "2322751077@qq.com")
        self.setupuser("test", "test114514", "test1@xiabeize.com")
        self.follow_user("KujoStar", self.jwt)
        res = self.client.get("/user/test/following?pageId=qq", content_type="application/json")
        json_response = res.json()
        self.assertEqual(res.status_code, 400)
        self.assertEqual(json_response['msg'], "Invalid params [pageId]")

    def test_change_user_nickname_success(self):
        self.setupuser("test", "123ewdughcvuwgy", "whfeuwigfeb")
        res = self.change_user_info("test", "Kujojojo", None, self.jwt)
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Succeed")
        self.assertEqual(res.status_code, 200)

    def test_change_user_slogan_success(self):
        self.setupuser("test", "123ewdughcvuwgy", "whfeuwigfeb")
        res = self.change_user_info("test", None, "1234643q", self.jwt)
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Succeed")
        self.assertEqual(res.status_code, 200)
        
    def test_change_user_nickname_and_slogan_success(self):
        self.setupuser("test", "123ewdughcvuwgy", "whfeuwigfeb")
        res = self.change_user_info("test", "weajojo", "1234643q", self.jwt)
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Succeed")
        self.assertEqual(res.status_code, 200)

    def change_nothing_success(self):
        self.setupuser("test", "123ewdughcvuwgy", "whfeuwigfeb")
        res = self.change_user_info("test", None, None, self.jwt)
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Succeed")
        self.assertEqual(res.status_code, 200)

    def test_change_others_info(self):
        self.setupuser("Kujo123", "1323refd", "2wdcf")
        res = self.change_user_info("Kujo123", "jojojo", None, self.jwt)
        json_response = res.json()
        self.assertEqual(json_response["msg"], "You can not edit other user's infomation.")
        self.assertEqual(res.status_code, 400)
        
    def test_change_not_found_info(self):
        res = self.change_user_info("qazwsxedc", "jojojojojo", None, self.jwt)
        json_response = res.json()
        self.assertEqual(json_response["msg"], "user not found")
        self.assertEqual(res.status_code, 404)

    def test_change_other_info_param(self):
        self.setupuser("test", "123ewdughcvuwgy", "whfeuwigfeb")
        res = self.client.put("/user/test", data={
            "username": "test123"
        }, HTTP_AUTHORIZATION=f"Bearer {self.jwt}", content_type="application/json")
        json_response = res.json()
        self.assertEqual(json_response["msg"], "You can only change your nickname and slogan.")
        self.assertEqual(res.status_code, 400)

    def test_change_nickname_too_long(self):
        self.setupuser("test", "123ewdughcvuwgy", "whfeuwigfeb")
        new_nickname = "114" * 100
        res = self.change_user_info("test", new_nickname, None, self.jwt)
        json_response = res.json()
        self.assertEqual(json_response["msg"], "new nickname too long")
        self.assertEqual(res.status_code, 400)

    def test_change_slogan_too_long(self):
        self.setupuser("test", "123ewdughcvuwgy", "whfeuwigfeb")
        new_slogan = "514" * 100
        res = self.change_user_info("test", None, new_slogan, self.jwt)
        json_response = res.json()
        self.assertEqual(json_response["msg"], "new slogan too long")
        self.assertEqual(res.status_code, 400)

    def test_get_user_image_with_not_exist_user(self):
        res = self.get_user_image("test156732")
        json_response = res.json()
        self.assertEqual(json_response['msg'], "user not found")
        self.assertEqual(res.status_code, 404)

    def test_get_user_image_with_invalid_param(self):
        self.setupuser("test", "123ewdughcvuwgy", "whfeuwigfeb")
        res = self.client.get("/user/test/images?sortedby=1234", content_type="applicaion/json")
        json_response = res.json()
        self.assertEqual(json_response['msg'], "Missing query parameters")
        self.assertEqual(res.status_code, 400)

    def test_get_user_image_empty(self):
        self.setupuser("test", "123ewdughcvuwgy", "whfeuwigfeb")
        res = self.client.get("/user/test/images", content_type="application/json")
        json_response = res.json()
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(json_response["result"]) == 0)
        self.assertEqual(json_response["count"], 0)
        self.assertEqual(json_response["perPage"], 20)


    def test_get_user_image_with_too_large_page(self):
        self.setupuser("test", "123ewdughcvuwgy", "whfeuwigfeb")
        user = User.objects.filter(username="test").first()
        image = AronaImage(content_type="gif", hash="1145141919810", uploader=user, width=114, height=514, title="testimage", description="test for image")
        image.save()
        res = self.client.get("/user/test/images?page=2&sortedBy=time", content_type="application/json")
        json_response = res.json()
        self.assertEqual(res.status_code, 400)

    def test_get_user_image_success(self):
        self.setupuser("test", "123ewdughcvuwgy", "whfeuwigfeb")
        user = User.objects.filter(username="test").first()
        image = AronaImage(content_type="gif", hash="11451419198110", uploader=user, width=114, height=514, title="testimage", description="test for image")
        image.save()
        res = self.client.get("/user/test/images", content_type="application/json")
        json_response = res.json()
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(json_response["result"]) != 0)
        self.assertEqual(json_response["count"], 1)
        expected_keys = {"id","hash","contentType","uploader","uploadTime", "likes","comments","width","height","title","tags","description","category"}
        self.assertEqual(expected_keys, set(json_response["result"][0].keys()))
        self.assertEqual(json_response["perPage"], 20)

    def test_get_user_image_success_more(self):
        self.setupuser("test", "123ewdughcvuwgy", "whfeuwigfeb")
        user = User.objects.filter(username="test").first()
        for i in range(0, 30):
            image = AronaImage(content_type="gif", hash="11451419198110", uploader=user, width=10 * i, height=514, title="testimage", description="test for image")
            image.save()

        res = self.client.get("/user/test/images", content_type="application/json")
        json_response = res.json()
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(json_response["result"]) == 20)
        self.assertEqual(json_response["count"], 30)
        expected_keys = {"id","hash","contentType","uploader","uploadTime", "likes","comments","width","height","title","tags","description","category"}
        self.assertEqual(expected_keys, set(json_response["result"][0].keys()))
        self.assertEqual(json_response["perPage"], 20)

    def test_get_user_image_success_with_page(self):
        self.setupuser("test", "123ewdughcvuwgy", "whfeuwigfeb")
        user = User.objects.filter(username="test").first()
        for i in range(0, 30):
            image = AronaImage(content_type="gif", hash="11451419198110", uploader=user, width=10 * i, height=514, title="testimage", description="test for image")
            image.save()

        res = self.client.get("/user/test/images?page=2&sortedBy=time", content_type="application/json")
        json_response = res.json()
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(json_response["result"]) == 10)
        self.assertEqual(json_response["count"], 30)
        expected_keys = {"id","hash","contentType","uploader","uploadTime", "likes","comments","width","height","title","tags","description","category"}
        self.assertEqual(expected_keys, set(json_response["result"][0].keys()))
        self.assertEqual(json_response["perPage"], 20)