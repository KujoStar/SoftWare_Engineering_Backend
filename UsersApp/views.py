from django.shortcuts import render
import json
import os
from django.http import HttpRequest, HttpResponse
from django.core.paginator import Paginator
from django.conf import settings
from UsersApp.config import *
from UsersApp.models import User, FollowRelation
from ImagesApp.models import AronaImage, AronaImageBrowseRecord
from utils.utils_request import BAD_METHOD, request_failed, request_success, return_field
from utils.utils_require import MAX_CHAR_LENGTH, CheckRequire, require
from utils.utils_time import get_timestamp
from blake3 import blake3
import jwt
import uuid
import base64
import random as rd
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
# Create your views here.

mail_host = settings.MAIL_HOST
mail_user = settings.MAIL_USER
mail_password = settings.MAIL_PASSWORD
sender = settings.MAIL_SENDER


def check_for_data_prelogin(body):
    user_name = require(body, "username", "string", err_msg="Missing or error type of [username]")
    assert 0 < len(user_name) < MAX_CHAR_LENGTH, "Too long username"
    
    return user_name


def check_for_data_preregister(body):
    user_name = require(body, "username", "string", err_msg="Missing or error type of [username]")
    user_email = require(body, "email", "string", err_msg="Missing or error type of [email]")


    return user_name, user_email


def check_for_legal_data_login(body):
    user_name = require(body, "username", "string", err_msg="Missing or error type of [username]")
    user_password = require(body, "password", "string", err_msg="Missing or error type of [password]")
    
    assert 0 < len(user_name) < MAX_CHAR_LENGTH, "Too long username"
    
    return user_name, user_password    


def check_for_legal_data_register(body):
    user_password = require(body, "password", "string", err_msg="Missing or error type of [password]")
    user_salt = require(body, "salt", "string", err_msg="Missing or error type of [salt]")
    user_code = require(body, "code", "string", err_msg="Missing or error type of [code]")
    return user_password, user_salt, user_code


@CheckRequire
def test(req: HttpRequest):
    return HttpResponse("114!514!Backend success!")


@CheckRequire
def preregister(req: HttpRequest):
    if req.method == "POST":
        body = json.loads(req.body.decode("utf-8"))
        req_name, req_email = check_for_data_preregister(body)
        user1 = User.objects.filter(username=req_name).first()
        if user1:
            if user1.password != "":
                return request_failed("Username has been registed", status_code=400)
            else:
                user1.delete()
        
        user2 = User.objects.filter(email=req_email).first()
        if user2:
            if user2.password != "":
                return request_failed("Email has been used", status_code=400)
            else:
                user2.delete()
        
        user_salt = uuid.uuid4()
        user_salt = str(user_salt)
        
        receivers = [req_email]
        msg = ''.join([rd.choice("0123456789") for _ in range(0, 6)])
        message = MIMEText(f"您的A.R.O.N.A注册验证码为 {msg}。\n\n若您没有进行注册操作，请忽略这一邮件。", "plain", "utf-8")
        message['Subject'] = "A.R.O.N.A注册"
        message['From'] = sender
        message['To'] = receivers[0]
        try:
            smtpobj = smtplib.SMTP()
            smtpobj.connect(mail_host, 25)
            smtpobj.login(mail_user, mail_password)
            smtpobj.sendmail(sender, receivers, message.as_string(), mail_options=[], rcpt_options=[])
            smtpobj.quit()
        except smtplib.SMTPException as e:
            print("ERROR:", e)
        
        user = User(username=req_name, email=req_email, salt=user_salt, mail_code=msg)
        user.save()
        return request_success({"salt": user_salt})
    
    else:
        return BAD_METHOD
    

@CheckRequire
def register(req: HttpRequest):
    if req.method == "POST":
        body = json.loads(req.body.decode("utf-8"))
        req_password, req_salt, req_code = check_for_legal_data_register(body)
        user = User.objects.filter(salt=req_salt).first()
        if not user:
            return request_failed("uuid not found", status_code=404)
        
        if user.mail_code != req_code:
            return request_failed("mail code incorrect", status_code=400)
        
        blake3hash_password = blake3(req_password.encode()).hexdigest()
        user.password = blake3hash_password
        user.salt = req_salt
        user.registerTime = get_timestamp()
        user.save()
        
        return request_success(status_code=201)
    
    else:
        return BAD_METHOD


@CheckRequire
def prelogin(req: HttpRequest):
    if req.method == "POST":
        body = json.loads(req.body.decode("utf-8"))
        req_name = check_for_data_prelogin(body)
        user1 = User.objects.filter(username=req_name).first()
        user2 = User.objects.filter(email=req_name).first()
        if not user1 and not user2:
            return request_failed("User not found", status_code=404)
        
        user = user1 if user1 else user2
        user_salt = user.salt
        return request_success({"salt": user_salt})
    
    else:
        return BAD_METHOD
    

@CheckRequire
def login(req: HttpRequest):
    if req.method == "POST":
        body = json.loads(req.body.decode("utf-8"))
        req_name, req_password = check_for_legal_data_login(body)
        user1 = User.objects.filter(username=req_name).first()
        user2 = User.objects.filter(email=req_name).first()
        if not user1 and not user2:
            return request_failed("User not found", status_code=404)
        
        user = user1 if user1 else user2
        blake3hash_password = blake3(req_password.encode()).hexdigest()
        if blake3hash_password != user.password:
            return request_failed("Password incorrect", status_code=400)
        
        payload = {
            "username": user.username,
            "nickname": user.nickname,
            "registerTime": user.registerTime,
            "userType": user.userType,
            "slogan": user.slogan,
            "email": user.email,
            "followingCount": user.followingCount,
            "followerCount": user.followerCount,
            "uploadCount": user.uploadCount,
        }
        token = jwt.encode(payload, settings.EDDSA_PRIVATE_KEY, algorithm="EdDSA")
        
        return request_success({"username": user.username, "jwt": token})
    
    else:
        return BAD_METHOD


@CheckRequire
def user_info(req: HttpRequest, username: any):
    user_name = require({"username": username}, "username", "string", err_msg="Bad param [username]")
    url = req.path_info
    user = User.objects.filter(username=user_name).first()
    if not user:
        return request_failed("user not found", 404)
    if user.password == '':
        return request_failed("user not found", 404)
    
    if req.method == "GET":
        if url == "/user/" + user_name:
            information = {
                "username": user.username,
                "nickname": user.nickname,
                "registerTime": user.registerTime,
                "userType": user.userType,
                "slogan": user.slogan,
                "email": user.email,
            }
            return request_success(information, status_code=200)
        
        elif url == "/user/" + user_name + "/detail":
            followstate = 0
            login_info = req.headers.get("authorization")
            if not login_info:
                followstate = 0
            else:
                token = login_info[7:]
                token_content = token.split(".")
                data = token_content[1]
                miss_padding = 4 - len(data) % 4
                if miss_padding:
                    data += '=' * miss_padding
                decoded_jwt = base64.b64decode(data).decode()
                jwt_json = json.loads(decoded_jwt)
                login_user = jwt_json['username']
                if user_name == login_user:
                    followstate = -1
                else:
                    follow1 = FollowRelation.objects.filter(follower=login_user, following=user_name).first()
                    follow2 = FollowRelation.objects.filter(follower=user_name, following=login_user).first()
                    if not follow1 and not follow2:
                        followstate = 0
                    if follow1 and not follow2:
                        followstate = 1
                    if not follow1 and follow2:
                        followstate = 2
                    if follow1 and follow2:
                        followstate = 3
            
            all_followers = list(FollowRelation.objects.filter(following=user_name))
            all_followings = list(FollowRelation.objects.filter(follower=user_name))
            user.followerCount = len(all_followers)
            user.followingCount = len(all_followings)
            user.save()
            detailed_information = {
                "username": user.username,
                "nickname": user.nickname,
                "registerTime": user.registerTime,
                "userType": user.userType,
                "slogan": user.slogan,
                "email": user.email,
                "followingCount": user.followingCount,
                "followerCount": user.followerCount,
                "uploadCount": user.uploadCount,
            }
            return_data = {"followState": followstate, **detailed_information}
            return request_success(return_data)
        
        elif url == "/user/" + user_name + "/follower":
            pagesize = int(20)
            pageid = int(1)
            params = req.GET
            keywords = params.keys()
            for key in keywords:
                if key not in ["pageSize", "pageId"]:
                    return request_failed("Invalid params", 400)
                
            if "pageSize" in keywords:
                query_pagesize = require(params, "pageSize", "string", err_msg="Bad param [pageSize]")
                if not query_pagesize.isdigit():
                    return request_failed("Invalid params [pageSize]", 400)
                
                pagesize = int(query_pagesize)
                
            if "pageId" in keywords:
                query_pageid = require(params, "pageId", "string", err_msg="Bad param [pageId]")
                if not query_pageid.isdigit():
                    return request_failed("Invalid params [pageId]", 400)
                
                pageid = int(query_pageid)
                
            all_followers = list(FollowRelation.objects.filter(following=user_name));
            if len(all_followers) == 0:
                return request_success({"followers": []})
        
            elif 0 < len(all_followers) <= (pageid - 1) * pagesize:
                return request_success({"followers": []})
            
            elif (pageid - 1) * pagesize < len(all_followers) < pageid * pagesize:
                return_data = [x.follower for x in all_followers[((pageid - 1) * pagesize):]]
                return request_success({"followers": return_data})
            
            elif len(all_followers) >= pageid * pagesize:
                return_data = [x.follower for x in all_followers[((pageid - 1) * pagesize):(pageid * pagesize)]]
                return request_success({"followers": return_data})
                
        elif url == "/user/" + user_name + "/following":
            pagesize = int(20)
            pageid = int(1)
            params = req.GET
            keywords = params.keys()
            for key in keywords:
                if key not in ["pageSize", "pageId"]:
                    return request_failed("Invalid params", 400)
                
            if "pageSize" in keywords:
                query_pagesize = require(params, "pageSize", "string", err_msg="Bad param [pageSize]")
                if not query_pagesize.isdigit():
                    return request_failed("Invalid params [pageSize]", 400)
                
                pagesize = int(query_pagesize)
                
            if "pageId" in keywords:
                query_pageid = require(params, "pageId", "string", err_msg="Bad param [pageId]")
                if not query_pageid.isdigit():
                    return request_failed("Invalid params [pageId]", 400)
                
                pageid = int(query_pageid)
                
            all_followings = list(FollowRelation.objects.filter(follower=user_name))
            if len(all_followings) == 0:
                return request_success({"followings": []})
        
            elif 0 < len(all_followings) <= (pageid - 1) * pagesize:
                return request_success({"followings": []})
            
            elif (pageid - 1) * pagesize < len(all_followings) < pageid * pagesize:
                return_data = [x.following for x in all_followings[((pageid - 1) * pagesize):]]
                return request_success({"followings": return_data})
            
            elif len(all_followings) >= pageid * pagesize:
                return_data = [x.following for x in all_followings[((pageid - 1) * pagesize):(pageid * pagesize)]]
                return request_success({"followings": return_data})
            
        else:
            return request_failed("path not found", 404)
        
    elif req.method == "PUT":
        if url == "/user/" + user_name:
            login_info = req.headers.get("authorization")
            token = ""
            if login_info:
                token = login_info[7:]
                
            token_content = token.split(".")
            data = token_content[1]
            miss_padding = 4 - len(data) % 4
            if miss_padding:
                data += '=' * miss_padding
            decoded_jwt = base64.b64decode(data).decode()
            jwt_json = json.loads(decoded_jwt)
            
            if user_name == jwt_json['username']:
                body = json.loads(req.body.decode("utf-8"))
                for key in body.keys():
                    if key not in ["nickname", "slogan"]:
                        return request_failed("You can only change your nickname and slogan.", 400)
                
                if "nickname" in body.keys():
                    new_nickname = body["nickname"]
                    if 0 < len(new_nickname) < MAX_CHAR_LENGTH:
                        user.nickname = new_nickname
                        user.save()
                    
                    else:
                        return request_failed("new nickname too long", 400)
                
                if "slogan" in body.keys():
                    new_slogan = body["slogan"]
                    if 0 < len(new_slogan) < MAX_CHAR_LENGTH:
                        user.slogan = new_slogan
                        user.save()
                    
                    else:
                        return request_failed("new slogan too long", 400)
                   
                return request_success()

            else:
                return request_failed("You can not edit other user's infomation.", 400)
            
        else:
            return request_failed("path not found", 404)
    
    elif req.method == "POST":
        login_info = req.headers.get("authorization")
        token = ""
        if login_info:
            token = login_info[7:]
        else:
            return request_failed("You haven't logged in yet.", 400)
        
        token_content = token.split(".")
        data = token_content[1]
        miss_padding = 4 - len(data) % 4
        if miss_padding:
            data += '=' * miss_padding
        decoded_jwt = base64.b64decode(data).decode()
        jwt_json = json.loads(decoded_jwt)
        operator_name = jwt_json['username']
        
        if url == "/user/" + user_name + "/follow":
            if operator_name == user_name:
                return request_failed("You cannot follow yourself.", 400)
            
            check = FollowRelation.objects.filter(follower=operator_name, following=user_name).first()
            if check:
                return request_failed(f"You have followed user {user_name}", 400)
            else:
                new_relation = FollowRelation(follower=operator_name, following=user_name)
                new_relation.save()
                follower = User.objects.filter(username=operator_name).first()
                follower.followingCount += 1
                follower.save()
                following = User.objects.filter(username=user_name).first()
                following.followerCount += 1
                following.save()
                return request_success()
        
        elif url == "/user/" + user_name + "/unfollow":
            if operator_name == user_name:
                return request_failed("You cannot unfollow yourself.", 400)
            
            current_relation = FollowRelation.objects.filter(follower=operator_name, following=user_name).first()
            if current_relation:
                current_relation.delete()
                follower = User.objects.filter(username=operator_name).first()
                follower.followingCount -= 1
                follower.save()
                following = User.objects.filter(username=user_name).first()
                following.followerCount -= 1
                following.save()
                return request_success()
            else:
                return request_failed("No such relation found", 404)
            
        else:
            return request_failed("path not found", 404)
            
    else:
        return BAD_METHOD
    

@CheckRequire
def user_image_info(req: HttpRequest, username: any):
    user_name = require({"username": username}, "username", "string", err_msg="Bad param [username]")
    
    if req.method == "GET":
        params = req.GET
        keywords = params.keys()

        if len(keywords) > 2:
            return request_failed("Too many query parameters", status_code=400)
        
        if len(keywords) != 0:
            if "page" not in keywords or "sortedBy" not in keywords:
                return request_failed("Missing query parameters", status_code=400)

        if len(keywords) == 0:
            page = 1
            sorted_by = "time"
        else:
            page = require(params, "page", "int", err_msg="Missing or error type of [page]")
            sorted_by = require(params, "sortedBy", "string", err_msg="Missing or error type of [sortedBy]")

        if sorted_by not in ["time"]:
            return request_failed("Invalid [sortedBy]", status_code=400)
        
        user = User.objects.filter(username=user_name).first()
        if user is None:
            return request_failed("user not found", 404)
        if user.password == '':
            return request_failed("user not found", 404)

        if sorted_by == "time":
            images = AronaImage.objects.filter(uploader=user).order_by('-upload_time')

        # Pagination
        image_pages = Paginator(images, USER_IMAGE_PER_PAGE)
        image_cnt = image_pages.count
        result_page = image_pages.page(page)

        return request_success(
            {
                "count": image_cnt,
                "perPage": USER_IMAGE_PER_PAGE,
                "result": [
                    {
                        "id": image.id,
                        "hash": image.hash,
                        "contentType": image.content_type,
                        "uploader": image.uploader.username,
                        "uploadTime": image.upload_time,
                        "likes": image.likes,
                        "comments": image.comments,
                        "width": image.width,
                        "height": image.height,
                        "title": image.title,
                        "tags": image.tags,
                        "description": image.description,
                        "category": image.category,
                    }
                for image in result_page],
            },
            status_code=200)

    else:
        return BAD_METHOD


@CheckRequire
def records(req: HttpRequest):
    if req.method == "GET":
        params = req.GET
        keywords = params.keys()
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
        jw_token = auth[7:]

        try:
            verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
            user = User.objects.filter(username=verification["username"]).first()
        except:
            return request_failed("Invalid digital signature", status_code=401)

        page = require(params, "page", "int", err_msg="Missing or error type of [page]", strict=False)
        if page is None:
            page = 1
        sorted_by = require(params, "sortedBy", "string", err_msg="Missing or error type of [sortedBy]", strict=False)
        if sorted_by is None:
            sorted_by = "time"

        if sorted_by not in ["time"]:
            return request_failed("Invalid [sortedBy]", status_code=400)
            
        if sorted_by == "time":
            records = AronaImageBrowseRecord.objects.filter(browser=user).order_by('-browse_time')
            image_id_list = [record.image.id for record in records]
            image_id_list = list(dict.fromkeys(image_id_list))  # unique

        reocrds = AronaImage.objects.filter(id__in=image_id_list)

        # Pagination
        record_pages = Paginator(reocrds, BROWSE_RECORD_PER_PAGE)
        record_cnt = record_pages.count
        result_page = record_pages.page(page)

        return request_success(
            {
                "count": record_cnt,
                "perPage": BROWSE_RECORD_PER_PAGE,
                "result": [
                    {
                        "id": image.id,
                        "hash": image.hash,
                        "contentType": image.content_type,
                        "uploader": image.uploader.username,
                        "uploadTime": image.upload_time,
                        "likes": image.likes,
                        "comments": image.comments,
                        "width": image.width,
                        "height": image.height,
                        "title": image.title,
                        "tags": image.tags,
                        "description": image.description,
                        "category": image.category,
                    }
                for image in result_page],
            },
            status_code=200)

    else:
        return BAD_METHOD