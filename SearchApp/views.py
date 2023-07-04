from django.shortcuts import render
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.core.paginator import Paginator
from UsersApp.models import User
from SearchApp.models import SearchModel
from SearchApp.config import SEARCH_RESULT_PER_PAGE, SEARCH_HISTORY_SIZE, MAX_ES_SEARCH_SIZE, MAX_ES_DETERMINED_STATES
from ImagesApp.models import AronaImage
from django.conf import settings
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from utils.utils_time import get_timestamp
from utils.utils_request import BAD_METHOD, request_failed, request_success
from utils.utils_require import MAX_CHAR_LENGTH, CheckPath, CheckRequire, require
import json 
import jwt
import requests
from urllib.parse import unquote

client = Elasticsearch(hosts=[settings.ES_HOST])


@CheckRequire
def search_image(req: HttpRequest):
    if req.method == "GET":
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]", strict=False)
        jw_token = auth[7:] if auth is not None else None
        if jw_token is not None:
            try:
                verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
                login_user = User.objects.filter(username=verification["username"]).first()
            except:
                return request_failed("Invalid digital signature", status_code=401)
            
        params = req.GET
        keywords = params.keys()

        search_for = require(params, "searchFor", "string", err_msg="Missing or error type of [searchFor]", strict=False)
        if search_for is None:
            search_for = ""
        search_for = unquote(unquote(search_for, 'utf-8'), 'utf-8')

        sorted_by = require(params, "sortBy", "string", err_msg="Missing or error type of [sortedBy]", strict=False)
        if sorted_by is None:
            sorted_by = "match"
        if sorted_by not in ["match", "uploadTime", "likes"]:
            return request_failed("Invalid sorting method", status_code=400)

        uploader = require(params, "uploader", "string", err_msg="Missing or error type of [uploader]", strict=False)
        if uploader is None:
            uploader = "all"

        page = require(params, "pageId", "int", err_msg="Missing or error type of [pageId]", strict=False)
        if page is None:
            page = 1

        category = require(params, "category", "string", err_msg="Missing or error type of [category]", strict=False)
        if category is None:
            category = "all"

        require_tag = req.GET.getlist("tags", [])

        width_min = require(params, "widthMin", "int", err_msg="Missing or error type of [widthMin]", strict=False)
        if width_min is None:
            width_min = 1
        width_max = require(params, "widthMax", "int", err_msg="Missing or error type of [widthMax]", strict=False)
        if width_max is None:
            width_max = 65536
        
        height_min = require(params, "heightMin", "int", err_msg="Missing or error type of [heightMin]", strict=False)
        if height_min is None:
            height_min = 1
        height_max = require(params, "heightMax", "int", err_msg="Missing or error type of [heightMax]", strict=False)
        if height_max is None:
            height_max = 65536
        
        regexp = require(params, "regexp", "int", err_msg="Missing or error type of [regexp]", strict=False)
        if regexp is None:
            regexp = 0

        if search_for == "" or set(search_for)== {' '} or search_for == ".*":
            all_images = AronaImage.objects.all()
            if not category == 'all':
                all_images = all_images.filter(category=category)
            if not uploader == 'all':
                specific_user = User.objects.filter(username=uploader).first()
                all_images = all_images.filter(uploader=specific_user)
            if require_tag != []:
                unquoted_tag = []
                for tag in require_tag:
                    real_tag = unquote(unquote(tag, 'utf-8'), 'utf-8')
                    unquoted_tag.append(real_tag)
                
                all_images = all_images.filter(tags__contains=unquoted_tag)
            
            all_images = all_images.filter(width__gte=width_min).filter(width__lte=width_max).filter(height__gte=height_min).filter(height__lte=height_max)
            
            if sorted_by == 'match':
                final_list = all_images
            if sorted_by == "uploadTime":
                final_list = all_images.order_by("-upload_time")
            if sorted_by == "likes":
                final_list = all_images.order_by("-likes")
                
            final_pages= Paginator(final_list, SEARCH_RESULT_PER_PAGE)
            count = final_pages.count
            return_page = final_pages.page(page)
            
            if jw_token is not None:
                if login_user is not None:
                    SearchModel.objects.create(
                        search_for= search_for,
                        search_user= login_user,
                    )

            return request_success({
                "count": count,
                "perPage": SEARCH_RESULT_PER_PAGE,
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
                        "isLiked": False
                    }
                for image in return_page]
            }, status_code=200)
            
        else:
            tag_list = analyzer(search_for, settings.ES_DB_NAME, regexp)

            unfilted_list = search_data(tag_list, settings.ES_DB_NAME)
            filted_list = []
            for item in unfilted_list:
                if "properties" not in item.keys():
                    flag = True
                    if not category == 'all':
                        if not item['category'] == category:
                            flag = False
                    if not uploader == 'all':
                        if not item['uploader'] == uploader:
                            flag = False
                    if require_tag != []:
                        for tag in require_tag:
                            real_tag = unquote(unquote(tag, 'utf-8'), 'utf-8')
                            if real_tag not in item['tags']:
                                flag = False
                                break
                    if item['width'] < width_min or item['width'] > width_max:
                        flag = False
                    if item['height'] < height_min or item['height'] > height_max:
                        flag = False
                    
                    if flag:
                        item['isLiked'] = False
                        filted_list.append(item)

            if sorted_by == 'match':
                filted_list = filted_list
            if sorted_by == "uploadTime":
                filted_list = sorted(filted_list, key=lambda x: x['uploadTime'], reverse=True)
            if sorted_by == "likes":
                filted_list = sorted(filted_list, key=lambda x: x['likes'], reverse=True)

            result_cnt = len(filted_list)
            result_page = filted_list[(page-1)*SEARCH_RESULT_PER_PAGE:page*SEARCH_RESULT_PER_PAGE]

            if jw_token is not None:
                if login_user is not None:
                    SearchModel.objects.create(
                        search_for= search_for,
                        search_user= login_user,
                    )

            return request_success({
                    "count": result_cnt,
                    "perPage": SEARCH_RESULT_PER_PAGE,
                    "result": result_page,
                }, status_code=200)

    else:
        return BAD_METHOD


def create_index(index_name, mapping):
    result = client.indices.create(index=index_name, body=mapping)
    return result


def search_data(query: list, index_name:str):  #根据分词列表，返回图片列表格式
    body = {
        "query": {
            "bool": {
                "should": query
            }
        }
    }
    url = "{}/{}/_search?size={}".format(settings.ES_HOST, index_name, MAX_ES_SEARCH_SIZE)
    headers = {"Content-Type": "application/json"}
    data = requests.post(url, headers=headers, data=json.dumps(body)).json()

    result = []
    if not data["timed_out"]:
        if not data["hits"]["total"]["value"] == 0:
            for hit in data["hits"]["hits"]:
                source = hit["_source"]
                result.append(source)
    return result


def analyzer(query: str, index_name: str, regexp: int):   #分词器，根据给定字符串，转化成对应模糊度的分词列表，这个请求列表可以直接传输给search_data使用
    if regexp == 0:
        url = "{}/{}/_analyze".format(settings.ES_HOST, index_name)
        data = {
            "tokenizer": "ik_smart",
            "text": query
        }
        headers = {"Content-Type": "application/json"}
        result = requests.post(url, headers=headers, data=json.dumps(data)).json()
        tokens = [{"token": token["token"], "start_offset": token["start_offset"], "end_offset": token["end_offset"]} for token in result["tokens"]]

        query_list = []
        for token in tokens:
            length = int(token['end_offset']) - int(token['start_offset'])
            fuziness = 0
            if length > 2:
                fuziness = 1
            single_query = {
                "match": {
                    "tags": {
                        "query": token['token'],
                        "fuzziness": fuziness,
                    }
                }
            }
            query_list.append(single_query)
            single_query = {
                "match": {
                    "title": {
                        "query": token['token'],
                        "fuzziness": fuziness,
                    }
                }
            }
            query_list.append(single_query)
            single_query =  {
                "match": {
                    "uploader": {
                        "query": token['token'],
                        "fuzziness": fuziness,
                    }
                }
            }
            query_list.append(single_query)
            single_query = {
                "match": {
                    "category": {
                        "query": token['token'],
                        "fuzziness": fuziness,
                    }
                }
            }
            query_list.append(single_query)
    
    elif regexp == 1:
        query_list = []
        single_query = {
            "regexp": {
                "tags": {
                    "value": query,
                    "flags": "ALL",
                    "max_determinized_states": MAX_ES_DETERMINED_STATES,
                }
            }
        }
        query_list.append(single_query)        
        single_query = {
            "regexp": {
                "uploader": {
                    "value": query,
                    "flags": "ALL",
                    "max_determinized_states": MAX_ES_DETERMINED_STATES,
                }
            }
        }
        query_list.append(single_query)        
        single_query = {
            "regexp": {
                "title": {
                    "value": query,
                    "flags": "ALL",
                    "max_determinized_states": MAX_ES_DETERMINED_STATES,
                }
            }
        }
        query_list.append(single_query)
        single_query = {
            "regexp": {
                "category": {
                    "value": query,
                    "flags": "ALL",
                    "max_determinized_states": MAX_ES_DETERMINED_STATES,
                }
            }
        }
        query_list.append(single_query)
    
    return query_list


@CheckRequire
def search_history(req: HttpRequest):
    if req.method == "GET":
        params = req.GET
        keywords = params.keys()

        search_for = require(params, "search_for", "string", err_msg="Missing or error type of [searchFor]", strict=False)
        if search_for is None:
            search_for = ""
        
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
        jw_token = auth[7:]
        try:
            verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
            user = User.objects.filter(username=verification["username"]).first()
        except:
            return request_failed("Invalid digital signature", status_code=401)
        
        histories = SearchModel.objects.filter(search_user=user).filter(search_for__startswith=search_for)\
            .exclude(deleted=True).order_by("-search_time")
        
        search_for_list = [history.search_for for history in histories]
        search_list = list(set(search_for_list))  # unique
        
        historoy_pages = Paginator(search_list, SEARCH_HISTORY_SIZE)
        history_cnt = historoy_pages.count
        history_page = historoy_pages.page(1)
        
        return request_success({
            "count": history_cnt,
            "perPage": SEARCH_HISTORY_SIZE,
            "result": [
                {
                    'search_for': history
                } 
            for history in history_page],
        }, 
        status_code = 200)

    else:  
        return BAD_METHOD


def has_exist(search_for: str, res: list):
    if search_for in res:
        return True
    else:
        return False


@CheckRequire
def search_user(req: HttpRequest):
    if req.method == "GET":
        params = req.GET
        keywords = params.keys()

        content = require(params, "content", "string", err_msg="Missing or error type of [content]", strict=False)
        if content is None:
            content = ""
        
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
        jw_token = auth[7:]
        try:
            verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
            user = User.objects.filter(username=verification["username"]).first()
        except:
            return request_failed("Invalid digital signature", status_code=401)
        
        if content == "":
            return request_success({"count": 0, "perPage": SEARCH_RESULT_PER_PAGE, "result": []})
        
        users = User.objects.filter(username__startswith=content).exclude(username=user.username).exclude(password="").order_by("username")
        user_pages = Paginator(users, SEARCH_RESULT_PER_PAGE)
        user_cnt = user_pages.count
        user_page = user_pages.page(1)

        return request_success({
            "count": user_cnt,
            "perPage": SEARCH_RESULT_PER_PAGE,
            "result": [user.serialize() for user in user_page],
        })
    
    else:
        return BAD_METHOD
