from django.conf import settings
import json
import jwt
import re
from blake3 import blake3
import os
import requests
from django.http import HttpRequest, HttpResponse
from UsersApp.models import User, FollowRelation
from ImagesApp.models import AronaImage
from SocialApp.models import Comment, LikeCommentRelation, LikeImageRelation
from utils.utils_request import BAD_METHOD, request_failed, request_success, get_es_id
from utils.utils_require import MAX_CHAR_LENGTH, CheckPath, CheckRequire, require
from SocialApp.config import *
from utils.utils_time import get_timestamp
from django.db.models import Q
from django.core.paginator import Paginator

@CheckRequire
def post_comment(req: HttpRequest):
    if req.method == "POST":
        body = json.loads(req.body.decode("utf-8").replace("'", '"'))
        content = require(body, "content", "string", err_msg="Missing or error type of [content]")
        belong_to_image_id = require(body, "belongToImageId", "int", err_msg="Missing or error type of [belongToImageId]")
        reply_to_comment_id = require(body, "replyToCommentId", "int", err_msg="Missing or error type of [replyToCommentId]", strict=False)
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
        jw_token = auth[7:] # remove "Bearer " from the authorization header

        try:
            verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
            poster = User.objects.filter(username=verification["username"]).first()
        except:
            return request_failed("Invalid digital signature", status_code=401)
        
        if not AronaImage.objects.filter(id=belong_to_image_id).exists():
            return request_failed("Image to comment not found", status_code=404)
    
        belong_to_image = AronaImage.objects.filter(id=belong_to_image_id).first()
        
        if reply_to_comment_id is None:
            comment = Comment.objects.create(content=content, poster=poster, belong_to_image=belong_to_image)
        else:
            reply_to_comment = Comment.objects.filter(id=reply_to_comment_id).first()
            if reply_to_comment.is_first_level():
                belong_to_comment = reply_to_comment
            else:
                belong_to_comment = reply_to_comment.belong_to_comment
            comment = Comment.objects.create(content=content, poster=poster, belong_to_image=belong_to_image, belong_to_comment=belong_to_comment,
                                             reply_to_comment=reply_to_comment, reply_to_user_username=reply_to_comment.poster.username)
 
        update_body = {
            "script": {
                "source": "ctx._source.comments += params.comments",
                "lang": "painless",
                "params": {
                    "comments": 1
                }
            }
        }
        es_id = get_es_id(belong_to_image_id)
        headers = {"Content-Type": "application/json"}
        if es_id != "":
            url = "{}/{}/_update/{}".format(settings.ES_HOST, settings.ES_DB_NAME, es_id)
            res = requests.post(url, headers=headers, data=json.dumps(update_body)).json()

        return request_success({"id": comment.id}, status_code=201)

    else:
        return BAD_METHOD
    

@CheckRequire
def comment_info(req: HttpRequest, id: int):
    comment_id = require({"id": id}, "id", "int", err_msg="Missing or error type of [comment id]")

    if req.method == "GET":
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]", strict=False)
        jw_token = auth[7:] if auth is not None else None

        if jw_token is not None:
            try:
                verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
                user = User.objects.filter(username=verification["username"]).first()
            except:
                return request_failed("Invalid digital signature", status_code=401)
            
        if not Comment.objects.filter(id=comment_id).exists():
            return request_failed("Comment not found", status_code=404)
        
        comment = Comment.objects.filter(id=comment_id).first()
        return request_success({
            "id": comment.id,
            "content": comment.content,
            "poster": comment.poster.username,
            "postTime": comment.post_time,
            "likes": comment.likes,
            "comments": comment.comments,
            "belongToImageId": comment.belong_to_image.id,
            "belongToCommentId": comment.belong_to_comment.id if comment.belong_to_comment is not None else None,
            "replyToCommentId": comment.reply_to_comment.id if comment.reply_to_comment is not None else None,
            "replyToUser": comment.reply_to_user_username if comment.reply_to_user_username is not None else None,
            "isLiked": False if jw_token is None else comment.is_liked_by(user),
        }, status_code=200)
    
    elif req.method == "DELETE":
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
        jw_token = auth[7:] # remove "Bearer " from the auth

        try:
            verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
            deleter = User.objects.filter(username=verification["username"]).first()
        except:
            return request_failed("Invalid digital signature", status_code=401)

        if not Comment.objects.filter(id=comment_id).exists():
            return request_failed("Comment not found", status_code=404)
        
        comment_to_delete = Comment.objects.filter(id=comment_id).first()
        if deleter != comment_to_delete.poster:
            return request_failed("You are not the poster of this comment", status_code=403)
        
        update_body = {
            "script": {
                "source": "ctx._source.comments -= params.comments",
                "lang": "painless",
                "params": {
                    "comments": 1 + comment_to_delete.comments
                }
            }
        }
        es_id = get_es_id(comment_to_delete.belong_to_image.id)
        headers = {"Content-Type": "application/json"}
        if es_id != "":
            url = "{}/{}/_update/{}".format(settings.ES_HOST, settings.ES_DB_NAME, es_id)
            res = requests.post(url, headers=headers, data=json.dumps(update_body)).json()

        comment_to_delete.delete()
        return request_success(status_code=200)

    else:
        return BAD_METHOD


@CheckRequire
def like_image(req: HttpRequest, id: int):
    image_id = require({"id": id}, "id", "int", err_msg="Missing or error type of [comment id]")

    if req.method == "PUT":
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
        jw_token = auth[7:] # remove "Bearer " from the auth

        try:
            verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
            user = User.objects.filter(username=verification["username"]).first()
        except:
            return request_failed("Invalid digital signature", status_code=401)

        image = AronaImage.objects.filter(id=image_id).first()
        if image is None:
            return request_failed("Image not found", status_code=404)
        
        likes_change = 0
        if image.is_liked_by(user):
            likes_change = -1
            LikeImageRelation.objects.filter(user=user, image=image).first().delete()
        else:
            likes_change = 1
            LikeImageRelation.objects.create(user=user, image=image)

        update_body = {
            "script": {
                "source": "ctx._source.likes += params.likes",
                "lang": "painless",
                "params": {
                    "likes": likes_change
                }
            }
        }
        es_id = get_es_id(image_id)
        headers = {"Content-Type": "application/json"}
        if es_id != "":
            url = "{}/{}/_update/{}".format(settings.ES_HOST, settings.ES_DB_NAME, es_id)
            res = requests.post(url, headers=headers, data=json.dumps(update_body)).json()

        return request_success(status_code=200)

    else:
        return BAD_METHOD


@CheckRequire
def like_comment(req: HttpRequest, id: int):
    comment_id = require({"id": id}, "id", "int", err_msg="Missing or error type of [comment id]")

    if req.method == "PUT":
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
        jw_token = auth[7:] # remove "Bearer " from the auth

        try:
            verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
            user = User.objects.filter(username=verification["username"]).first()
        except:
            return request_failed("Invalid digital signature", status_code=401)
        
        comment = Comment.objects.filter(id=comment_id).first()
        if comment is None:
            return request_failed("Comment not found", status_code=404)

        if comment.is_liked_by(user):
            LikeCommentRelation.objects.filter(user=user, comment=comment).first().delete()
        else:
            LikeCommentRelation.objects.create(user=user, comment=comment)
        return request_success(status_code=200)
    
    else:
        return BAD_METHOD


@CheckRequire
def dynamic_list(req: HttpRequest):
    if req.method == "GET":
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
        jw_token = auth[7:]

        try:
            verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
            login_user = User.objects.filter(username=verification["username"]).first()
        except:
            return request_failed("Invalid digital signature", status_code=401)
        
        login_user.last_view_folllowing_moment = get_timestamp()
        login_user.save()
        
        query_param = Q()
        query_param.connector = 'OR'
        all_followings = FollowRelation.objects.filter(follower=login_user.username)
        for relation in all_followings:
            cur_user = User.objects.filter(username=relation.following).first()
            query_param.children.append(('uploader', cur_user))
        
        all_images = AronaImage.objects.filter(query_param).order_by("-upload_time")
        pageId = int(req.GET.get("pageId", 1))
        image_pages = Paginator(all_images, FOLLOWING_IMAGE_PER_PAGE)
        count = image_pages.count
        result_page = image_pages.page(pageId)
        
        return request_success(
            {
                "count": count,
                "perPage": FOLLOWING_IMAGE_PER_PAGE,
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
                for image in result_page]
            },
       )
    
    else:
        return BAD_METHOD
    
@CheckRequire
def dynamic_unread(req: HttpRequest):
    if req.method == "GET":
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
        jw_token = auth[7:]

        try:
            verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
            login_user = User.objects.filter(username=verification["username"]).first()
        except:
            return request_failed("Invalid digital signature", status_code=401)
        
        all_time_list = []
        all_followings = FollowRelation.objects.filter(follower=login_user.username)
        for relation in all_followings:
            cur_user = User.objects.filter(username=relation.following).first()
            image_uploaded_by_user = AronaImage.objects.filter(uploader=cur_user)
            for image in image_uploaded_by_user:
                all_time_list.append(image.upload_time)

        all_time_list = sorted(all_time_list, key=lambda x: x, reverse=True)
        last_view_time = login_user.last_view_folllowing_moment
        count = 0
        for time in all_time_list:
            if time > last_view_time:
                count += 1

        return request_success({"count": count}, status_code=200)
    
    else:
        return BAD_METHOD