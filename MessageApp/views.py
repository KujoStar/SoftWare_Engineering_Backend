from django.shortcuts import render
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.core.paginator import Paginator
from UsersApp.models import User
from MessageApp.models import Message
from utils.utils_require import MAX_TEXT_LENGTH, CheckRequire, require
from utils.utils_request import BAD_METHOD, request_failed, request_success, return_field
import jwt, json
from MessageApp.config import MESSAGE_PER_PAGE
from django.conf import settings


@CheckRequire
def record(req: HttpRequest):
	if req.method == "GET":
		auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
		jw_token = auth[7:]
		try:
			verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
			user = User.objects.filter(username=verification["username"]).first()
		except:
			return request_failed("Invalid digital signature", status_code=401)
		
		params = req.GET
		keywords = params.keys()
		
		page = require(params, "pageId", "int", err_msg="Missing or error type of [pageId]", strict=False)
		if page is None:
			page = 1
		req_name = require(params, "username", "string", err_msg="Missing or error type of [username]")

		if req_name == user.username:
			return request_success({"count": 0, "perPage": MESSAGE_PER_PAGE, "result": []})
		
		another = User.objects.filter(username=req_name).first()
		if another is None:
			return request_failed("User not found", status_code=404)

		records_A = Message.objects.filter(deleted=False, sender=user, receiver=another)

		records_B = Message.objects.filter(deleted=False, sender=another, receiver=user)
		unread_messages = records_B.filter(is_read=False)
		unread_messages.update(is_read=True)

		# 合为一体
		records = (records_A | records_B).order_by('-time')
		record_pages = Paginator(records, MESSAGE_PER_PAGE)
		record_cnt = record_pages.count
		result_page = record_pages.page(page)

		return request_success({
			"count": record_cnt,
			"perPage": MESSAGE_PER_PAGE, 
			"result": [record.serialize() for record in result_page],
		})
	
	else:
		return BAD_METHOD


@CheckRequire
def send(req: HttpRequest):
	if req.method == "POST":
		params = req.GET
		keywords = params.keys()
		
		req_name = require(params, "username", "string", err_msg="Missing or error type of [username]")

		receiver = User.objects.filter(username=req_name).first()
		if receiver is None:
			return request_failed("User not found", status_code=404)
		
		auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
		jw_token = auth[7:]
		try:
			verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
			sender = User.objects.filter(username=verification["username"]).first()
		except:
			return request_failed("Invalid digital signature", status_code=401)
		
		body = json.loads(req.body.decode("utf-8").replace("'", '"'))
		content = require(body, "content", "string", err_msg="Missing or error type of [content]")

		if (len(content) > MAX_TEXT_LENGTH):
			return request_failed("Payload too large", status_code=413)

		message = Message(sender=sender, receiver=receiver, content=content)
		message.save()
		
		return request_success({"id": message.id, "time": message.time}, status_code=201)
	else:
		return BAD_METHOD
	

@CheckRequire
def recent(req: HttpRequest):
	if req.method == "GET":
		params = req.GET
		keywords = params.keys()

		page = require(params, "pageId", "int", err_msg="Missing or error type of [pageId]", strict=False)
		if page is None:
			page = 1
		
		auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
		jw_token = auth[7:]
		try:
			verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
			user = User.objects.filter(username=verification["username"]).first()
		except:
			return request_failed("Invalid digital signature", status_code=401)
		
		messages = Message.objects.filter(deleted=False).filter(Q(sender=user) | Q(receiver=user)).order_by('-time')

		existed = set()
		result = list()
		
		for message in messages:
			another = message.another(user)
			if not another in existed:
				existed.add(another)
				result.append(message)

		record_pages = Paginator(result, MESSAGE_PER_PAGE)
		record_cnt = record_pages.count
		result_page = record_pages.page(page)

		
		return request_success({
			"count": record_cnt, 
			"perPage": MESSAGE_PER_PAGE, 
			"result": [record.serialize() for record in result_page],
		})
	
	else:
		return BAD_METHOD


@CheckRequire
def unread(req: HttpRequest):
	if req.method == "GET":
		auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
		jw_token = auth[7:]
		try:
			verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
			user = User.objects.filter(username=verification["username"]).first()
		except:
			return request_failed("Invalid digital signature", status_code=401)
		
		count = Message.objects.filter(deleted=False, receiver=user, is_read=False).count()
		
		return request_success({"count": count})
	
	else:
		return BAD_METHOD


@CheckRequire
def delete(req: HttpRequest):
	if req.method == "DELETE":
		params = req.GET
		keywords = params.keys()

		message_id = require(params, "pageId", "int", err_msg="Missing or error type of [pageId]")
		
		auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
		jw_token = auth[7:]
		try:
			verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
			user = User.objects.filter(username=verification["username"]).first()
		except:
			return request_failed("Invalid digital signature", status_code=401)
		
		message = Message.objects.filter(id=message_id).first()
		
		if (message.sender.username != user.username):
			return request_failed("Forbidden behavior", status_code=403)

		if (message.deleted):
			return request_failed("Not found", status_code=404)
		
		message.update(deleted=True)
		
		return request_success()
	
	else:
		return BAD_METHOD
