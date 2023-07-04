from django.http import JsonResponse
from django.conf import settings
import requests
import json

def request_failed(info, status_code=400):
    return JsonResponse({
        "msg": info
    }, status=status_code)


def request_success(data={}, status_code=200):
    return JsonResponse({
        "msg": "Succeed",
        **data
    }, status=status_code)


def return_field(obj_dict, field_list):
    for field in field_list:
        assert field in obj_dict, f"Field `{field}` not found in object."

    return {
        k: v for k, v in obj_dict.items()
        if k in field_list
    }


def get_es_id(image_id):
    url = "{}/{}/_search".format(settings.ES_HOST, settings.ES_DB_NAME)
    headers = {"Content-Type": "application/json"}
    body = {
        "query": {
            "match": {
                "id": image_id
            }
        }
    }
    id = ""
    res = requests.get(url, headers=headers, data=json.dumps(body)).json()
    if not res["timed_out"]:
        if not res["hits"]["total"]["value"] == 0:
            id = res["hits"]["hits"][0]["_id"]

    return id


BAD_METHOD = request_failed("Bad method", 405)