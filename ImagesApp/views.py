from django.conf import settings
import json
import io
import time
import base64
import jwt
import re
import uuid
from datetime import timedelta
from blake3 import blake3
import os
import cv2
import ffmpeg
from PIL import Image, ImageSequence, ImageFont, ImageDraw
import imageio
import matplotlib.font_manager as fm
import requests
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.core.paginator import Paginator
from ImagesApp.config import COMMENT_PER_PAGE, UTIL_RESULT_PER_PAGE, FONT_SIZE, TMP_DIR, IMAGE_CATEGORIES
from UsersApp.models import User
from ImagesApp.models import AronaImage, AronaImageBrowseRecord, ImageUtilRecord
from SocialApp.models import Comment
from qcloud_cos import CosConfig, CosS3Client
from utils import utils_time
from utils.utils_request import BAD_METHOD, request_failed, request_success, return_field, get_es_id
from utils.utils_require import MAX_CHAR_LENGTH, CheckPath, CheckRequire, require

client = CosS3Client(CosConfig(Region=settings.COS_REGION, SecretId=settings.COS_SECRET_ID, SecretKey=settings.COS_SECRET_KEY))


def change_to_tmp_dir():
    os.chdir(TMP_DIR)


@CheckPath
def create_roughver(image_name: str, quality: int=50):
    """Create the low-quality version of the image file.

    Args:
        image_name: the whole filename of the image file to be converted.

    Returns:
        the whole filename of the created low-quality version.
    """
    format = image_name.split('.')[-1]
    image_id = image_name[:-(len(format) + 1)]

    if format == 'gif':
        image = Image.open(image_name)
        duration = image.info['duration']

        with imageio.get_reader(image_name) as reader:
            frames = [Image.fromarray(frame) for frame in reader]

        save_name = image_id + '.webp'
        frames[0].save(save_name, format='WEBP', save_all=True, append_images=frames[1:], optimize=True, quality=quality, duration=duration, loop=0)
        return save_name
    
    elif format == 'jpeg':
        im = Image.open(image_name)
        save_name = image_id + '.webp'
        im.save(save_name, format='WEBP', optimize=True, quality=quality)
        return save_name
    
    elif format == 'png':
        im = Image.open(image_name)
        save_name = image_id + '.webp'
        im.save(save_name, format='WEBP', optimize=True, quality=quality)
        return save_name


@CheckPath
def fput_object(image_name: str, blake3_hash: str):
    """Put an object and its webp version in the workspace directory /opt/tmp to the COS server.

    Args:
        format: the format of the object, deciding the bucket to be put in.
        blake3_hash: the blake3 hash of the object, and name it accordingly.

    Returns:
        the writting result of the object.
    """
    format = image_name.split('.')[-1]
    image_id = image_name[:-(len(format) + 1)]

    if format == 'gif':
        try:
            client.upload_file(
                Bucket=settings.GIF_BUCKET,
                Key=blake3_hash,
                LocalFilePath=image_name,
                ContentType=f"image/gif"
            )
            webp_name = create_roughver(image_name)
            client.upload_file(
                Bucket=settings.ROUGH_GIF_BUCKET,
                Key=blake3_hash,
                LocalFilePath=webp_name,
                ContentType=f"image/webp"
            )
        except Exception as err:
            raise err
        
    elif format == 'jpeg':
        try:
            client.upload_file(
                Bucket=settings.JPEG_BUCKET,
                Key=blake3_hash,
                LocalFilePath=image_name,
                ContentType=f"image/jpeg"
            )
            webp_name = create_roughver(image_name)
            client.upload_file(
                Bucket=settings.ROUGH_JPEG_BUCKET,
                Key=blake3_hash,
                LocalFilePath=webp_name,
                ContentType=f"image/webp"
            )
        except Exception as err:
            raise err
        
    elif format == 'png':
        try:
            client.upload_file(
                Bucket=settings.PNG_BUCKET,
                Key=blake3_hash,
                LocalFilePath=image_name,
                ContentType=f"image/png"
            )
            webp_name = create_roughver(image_name)
            client.upload_file(
                Bucket=settings.ROUGH_PNG_BUCKET,
                Key=blake3_hash,
                LocalFilePath=webp_name,
                ContentType=f"image/webp"
            )
        except Exception as err:
            raise err

    else:
        raise ValueError("Invalid format")

    return image_name, webp_name


@CheckPath
def fput_util_result(image_name: str, blake3_hash: str, util_type: str):
    format = image_name.split('.')[-1]
    image_id = image_name[:-(len(format) + 1)]

    if util_type == "convert":
        try:
            client.upload_file(
                Bucket=settings.CONVERT_BUCKET,
                Key=blake3_hash,
                LocalFilePath=image_name,
                ContentType=f"image/{format}"
            )
        except Exception as err:
            raise err
    
    elif util_type == "resolution":
        try:
            client.upload_file(
                Bucket=settings.RESOLUTION_BUCKET,
                Key=blake3_hash,
                LocalFilePath=image_name,
                ContentType=f"image/{format}"
            )
        except Exception as err:
            raise err
        
    elif util_type == "watermark":
        try:
            client.upload_file(
                Bucket=settings.WATERMARK_BUCKET,
                Key=blake3_hash,
                LocalFilePath=image_name,
                ContentType=f"image/{format}"
            )
        except Exception as err:
            raise err
        
    else:
        raise ValueError("Invalid util type")
    

@CheckPath
def fget_object(dest_name: str, format: str, blake3_hash: str, rough: bool=False):
    """Get an object from the COS server and save it to the workspace directory /opt/tmp.

    Args:
        format: the format of the object, simplifying the process of bucket selection.
        blake3_hash: the blake3 hash of the object in the certain bucket.    

    Returns:
        the object in the certain bucket.
    """

    if format == 'gif':
        bucket = settings.ROUGH_GIF_BUCKET if rough else settings.GIF_BUCKET
    elif format == 'jpeg':
        bucket = settings.ROUGH_JPEG_BUCKET if rough else settings.JPEG_BUCKET
    elif format == 'png':
        bucket = settings.ROUGH_PNG_BUCKET if rough else settings.PNG_BUCKET
    else:
        raise ValueError("Invalid format")

    try:
        client.download_file(
            Bucket=bucket,
            Key=blake3_hash,
            DestFilePath=dest_name,
            ResponseContentType=f"image/{'webp' if rough else format}"
        )
    except Exception as err:
        raise err


@CheckPath
def fget_util_result(image_name: str, blake3_hash: str, util_type: str):
    format = image_name.split('.')[-1]
    image_id = image_name[:-(len(format) + 1)]

    if util_type == "convert":
        try:
            client.download_file(
                Bucket=settings.CONVERT_BUCKET,
                Key=blake3_hash,
                DestFilePath=image_name,
                ResponseContentType=f"image/{format}"
            )
        except Exception as err:
            raise err
    
    elif util_type == "resolution":
        try:
            client.download_file(
                Bucket=settings.RESOLUTION_BUCKET,
                Key=blake3_hash,
                DestFilePath=image_name,
                ResponseContentType=f"image/{format}"
            )
        except Exception as err:
            raise err
        
    elif util_type == "watermark":
        try:
            client.download_file(
                Bucket=settings.WATERMARK_BUCKET,
                Key=blake3_hash,
                DestFilePath=image_name,
                ResponseContentType=f"image/{format}"
            )
        except Exception as err:
            raise err
        
    else:
        raise ValueError("Invalid util type")
    
    
def presigned_fget_object(format: str, blake3_hash: str, expiry: int):
    """Get a presigned url of an original object from the COS server.

    Args:
        format: the format of the object, simplifying the process of bucket selection.
        blake3_hash: the blake3 hash of the object in the certain bucket.
        expiry: the expiry time of the presigned url, in seconds.

    Returns:
        the presigned url of the original object in the certain bucket.
    """
    if format == 'gif':
        bucket = settings.GIF_BUCKET
    elif format == 'jpeg':
        bucket = settings.JPEG_BUCKET
    elif format == 'png':
        bucket = settings.PNG_BUCKET
    else:
        raise ValueError("Invalid format")
    
    try:
        return client.get_presigned_url(
            Method='GET',
            Bucket=bucket,
            Key=blake3_hash,
            Expired=expiry
        )
    except Exception as err:
        raise err
    

@CheckRequire
def video2gif(req: HttpRequest):
    if req.method == "POST":
        video = req.FILES.get("video", None)
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
        jw_token = auth[7:] # remove "Bearer " from the authorization header

        try:
            verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
            user = User.objects.get(username=verification["username"])
        except:
            return request_failed("Invalid digital signature", status_code=401)
        
        if video is None:
            return request_failed("Missing video", status_code=400)
        
        video_type = video.content_type.split('/')[-1]
        if video_type not in ["mp4", "x-matroska"]:
            return request_failed("Invalid file type", status_code=400)
        
        params = req.GET
        keywords = params.keys()

        if len(keywords) > 3:
            return request_failed("Too many query parameters", status_code=400)

        if len(keywords) == 0:
            change_to_tmp_dir()
            video_type_format = "mkv" if video_type == "x-matroska" else "mp4"
            video_name = str(uuid.uuid4()) + '.' + video_type_format
            convgif_name = str(uuid.uuid4()) + '.gif'
            with open(video_name, "wb") as f:
                for chunk in video.chunks():
                    f.write(chunk)
            
            ffmpeg.input(video_name).output(convgif_name).run()

            with open(convgif_name, "rb") as f:
                blake3_hash = blake3(f.read()).hexdigest()
            fput_util_result(convgif_name, blake3_hash, "convert")

            os.remove(video_name)
            os.remove(convgif_name)
            
            ImageUtilRecord.objects.create(
                user=user,
                result_url=client.get_presigned_url(
                    Method='GET',
                    Bucket=settings.CONVERT_BUCKET,
                    Key=blake3_hash,
                    Expired=timedelta(days=7).total_seconds()
                ),
                result_type="gif",
                util_type="convert",
            )
            return request_success(status_code=200)

        if "start" not in keywords or "end" not in keywords or "resize" not in keywords:
            return request_failed("Missing query parameters", status_code=400)

        start = require(params, "start", "float", err_msg="Missing or error type of [start]")
        end = require(params, "end", "float", err_msg="Missing or error type of [end]")
        resize = require(params, "resize", "float", err_msg="Missing or error type of [resize]")

        change_to_tmp_dir()
        video_type_format = "mkv" if video_type == "x-matroska" else "mp4"
        video_name = str(uuid.uuid4()) + '.' + video_type_format
        convvideo_name = str(uuid.uuid4()) + '.' + video_type_format
        convgif_name = str(uuid.uuid4()) + '.gif'
        with open(video_name, "wb") as f:
            for chunk in video.chunks():
                f.write(chunk)

        cap = cv2.VideoCapture(video_name)
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        except:
            return request_failed("Video file is broken", status_code=400)
        
        start_frame = int(start * fps)
        end_frame = int(end * fps)
        new_frames = end_frame - start_frame + 1
        new_width = int(width * resize)
        new_height = int(height * resize)

        if video_type_format == "mkv":
            fourcc = cv2.VideoWriter_fourcc(*'X264')
        elif video_type_format == "mp4":
            fourcc = cv2.VideoWriter_fourcc(*'MP4V')
        out = cv2.VideoWriter(convvideo_name, fourcc, fps, (new_width, new_height))

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        for _ in range(new_frames):
            ret, frame = cap.read()
            if not ret: break
            frame = cv2.resize(frame, (new_width, new_height))
            out.write(frame)

        cap.release()
        out.release()

        ffmpeg.input(convvideo_name).output(convgif_name).run()

        with open(convgif_name, "rb") as f:
            blake3_hash = blake3(f.read()).hexdigest()
        fput_util_result(convgif_name, blake3_hash, "convert")

        os.remove(video_name)
        os.remove(convvideo_name)
        os.remove(convgif_name)

        ImageUtilRecord.objects.create(
                user=user,
                result_url=client.get_presigned_url(
                    Method='GET',
                    Bucket=settings.CONVERT_BUCKET,
                    Key=blake3_hash,
                    Expired=timedelta(days=7).total_seconds()
                ),
                result_type="gif",
                util_type="convert"
            )
        return request_success(status_code=200)

    else:
        return BAD_METHOD
    

@CheckRequire
def super_resolution(req: HttpRequest):
    if req.method == "POST":
        image = req.FILES.get("image", None)
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
        jw_token = auth[7:] # remove "Bearer " from the authorization header

        try:
            verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
            user = User.objects.get(username=verification["username"])
        except:
            return request_failed("Invalid digital signature", status_code=401)
        
        if image is None:
            return request_failed("Missing image", status_code=400)

        image_type = image.content_type.split('/')[-1]
        if image_type not in ["gif", "jpeg", "png"]:
            return request_failed("Invalid file type", status_code=400)
        if image_type == "gif":
            version = Image.open(image).info['version']
            if version == b'GIF87a':
                return request_failed("GIF87a is not supported", status_code=400)
    
        api_url = "https://aip.baidubce.com/rest/2.0/image-process/v1/image_definition_enhance"
        request_url = api_url + "?access_token=" + settings.BAIDU_AI_TOKEN

        if image_type == "gif":
            change_to_tmp_dir()
            gif_name = str(uuid.uuid4()) + '.gif'
            with open(gif_name, "wb") as f:
                for chunk in image.chunks():
                    f.write(chunk)

            image = Image.open(gif_name)
            duration = image.info['duration']
    
            with imageio.get_reader(gif_name) as reader:
                frames = [Image.fromarray(frame) for frame in reader]
                sr_frames = []

            for idx, frame in enumerate(frames):
                frame_name = str(uuid.uuid4()) + '.png'
                frame.save(frame_name, format="PNG")
                with open(frame_name, "rb") as f:
                    image_b64bytes = base64.b64encode(f.read())
                while True:
                    response = requests.post(
                        url=request_url,
                        data={"image": image_b64bytes},
                        headers={"content-type": "application/x-www-form-urlencoded"},
                    )
                    if "image" in response.json(): break
                image_bytes = base64.b64decode(response.json()["image"])
                sr_frames.append(Image.open(io.BytesIO(image_bytes)))
                os.remove(frame_name)

            resogif_name = str(uuid.uuid4()) + '.gif'
            sr_frames[0].save(resogif_name, save_all=True, duration=duration, loop=0, append_images=sr_frames[1:])

            with open(resogif_name, "rb") as f:
                blake3_hash = blake3(f.read()).hexdigest()
            fput_util_result(resogif_name, blake3_hash, "resolution")

            os.remove(gif_name)
            os.remove(resogif_name)

            ImageUtilRecord.objects.create(
                user=user,
                result_url=client.get_presigned_url(
                    Method='GET',
                    Bucket=settings.RESOLUTION_BUCKET,
                    Key=blake3_hash,
                    Expired=timedelta(days=7).total_seconds()
                ),
                result_type="gif",
                util_type="resolution"
            )
            return request_success(status_code=200)

        elif image_type == "jpeg":
            change_to_tmp_dir()
            image_b64bytes = base64.b64encode(image.read())
            response = requests.post(
                url=request_url,
                data={"image": image_b64bytes},
                headers={"content-type": "application/x-www-form-urlencoded"},
            )
            image_bytes = base64.b64decode(response.json()["image"])
            blake3_hash = blake3(image_bytes).hexdigest()

            resojpeg_name = str(uuid.uuid4()) + '.jpeg'
            with open(resojpeg_name, "wb") as f:
                f.write(image_bytes)
            fput_util_result(resojpeg_name, blake3_hash, "resolution")

            os.remove(resojpeg_name)

            ImageUtilRecord.objects.create(
                user=user,
                result_url=client.get_presigned_url(
                    Method='GET',
                    Bucket=settings.RESOLUTION_BUCKET,
                    Key=blake3_hash,
                    Expired=timedelta(days=7).total_seconds()
                ),
                result_type="jpeg",
                util_type="resolution"
            )
            return request_success(status_code=200)

        elif image_type == "png":
            change_to_tmp_dir()
            image_b64bytes = base64.b64encode(image.read())
            response = requests.post(
                url=request_url,
                data={"image": image_b64bytes},
                headers={"content-type": "application/x-www-form-urlencoded"},
            )
            image_bytes = base64.b64decode(response.json()["image"])
            blake3_hash = blake3(image_bytes).hexdigest()

            resopng_name = str(uuid.uuid4()) + '.png'
            with open(resopng_name, "wb") as f:
                f.write(image_bytes)
            fput_util_result(resopng_name, blake3_hash, "resolution")

            os.remove(resopng_name)

            ImageUtilRecord.objects.create(
                user=user,
                result_url=client.get_presigned_url(
                    Method='GET',
                    Bucket=settings.RESOLUTION_BUCKET,
                    Key=blake3_hash,
                    Expired=timedelta(days=7).total_seconds()
                ),
                result_type="png",
                util_type="resolution"
            )
            return request_success(status_code=200)

        else:
            raise TypeError("Unsupported image format.")

    else:
        return BAD_METHOD
    

@CheckRequire
def watermark(req: HttpRequest):
    if req.method == "POST":
        image = req.FILES.get("image", None)
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
        jw_token = auth[7:] # remove "Bearer " from the authorization header

        try:
            verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
            user = User.objects.filter(username=verification["username"]).first()
        except:
            return request_failed("Invalid digital signature", status_code=401)
        
        if image is None:
            return request_failed("Missing image", status_code=400)
        
        im = Image.open(image)
        if im.format not in ["GIF", "PNG", "JPEG"]:
            return request_failed("Invalid file type", status_code=400)
        if im.format == "GIF":
            if im.info['version'] == b'GIF87a':
                return request_failed("GIF87a is not supported", status_code=400)

        params = req.GET
        keywords = params.keys()

        if len(keywords) > 4:
            return request_failed("Too many query parameters", status_code=400)
        
        width, height = im.size
        font = fm.findfont(fm.FontProperties(family='DejaVu Sans', style='oblique', weight='normal'))
        
        if len(keywords) == 0:
            text = "A.R.O.N.A@{}".format(user.username)
            font_size_ratio = 3
            width_pos_ratio = 5
            height_pos_ratio = 93
        else:
            if "text" not in keywords or "fontSize" not in keywords or "widthPos" not in keywords or "heightPos" not in keywords:
                return request_failed("Missing query parameters", status_code=400)
            text = require(params, "text", "string", err_msg="Missing or error type of [text]")
            font_size_ratio = require(params, "fontSize", "int", err_msg="Missing or error type of [fontSize]")
            width_pos_ratio = require(params, "widthPos", "int", err_msg="Missing or error type of [widthPos]")
            height_pos_ratio = require(params, "heightPos", "int", err_msg="Missing or error type of [heightPos]")

        font_size = int(min(width, height) * float(font_size_ratio) / 100)
        width_pos = int(width * float(width_pos_ratio) / 100)
        height_pos = int(height * float(height_pos_ratio) / 100)
    
        if im.format == "GIF":
            change_to_tmp_dir()
            frames = []
            duration = im.info['duration']
            for frame in ImageSequence.Iterator(im):
                frame = frame.convert("RGB")
                draw = ImageDraw.Draw(frame)
                draw.text(xy=(width_pos, height_pos), text=text, fill="white", font=ImageFont.truetype(font, font_size))
                frames.append(frame)
            gif_name = str(uuid.uuid4()) + '.gif'
            frames[0].save(gif_name, save_all=True, duration=duration, loop=0, append_images=frames[1:])

            with open(gif_name, "rb") as f:
                blake3_hash = blake3(f.read()).hexdigest()
            fput_util_result(gif_name, blake3_hash, "watermark")

            os.remove(gif_name)

            ImageUtilRecord.objects.create(
                user=user,
                result_url=client.get_presigned_url(
                    Method='GET',
                    Bucket=settings.WATERMARK_BUCKET,
                    Key=blake3_hash,
                    Expired=timedelta(days=7).total_seconds()
                ),
                result_type="gif",
                util_type="watermark"
            )
            return request_success(status_code=200)
    
        elif im.format == "JPEG":
            change_to_tmp_dir()
            draw = ImageDraw.Draw(im)
            draw.text(xy=(width_pos, height_pos), text=text, fill="white", font=ImageFont.truetype(font, font_size))
            jpeg_name = str(uuid.uuid4()) + '.jpeg'
            im.save(jpeg_name, "JPEG")
            
            with open(jpeg_name, "rb") as f:
                blake3_hash = blake3(f.read()).hexdigest()
            fput_util_result(jpeg_name, blake3_hash, "watermark")

            os.remove(jpeg_name)

            ImageUtilRecord.objects.create(
                user=user,
                result_url=client.get_presigned_url(
                    Method='GET',
                    Bucket=settings.WATERMARK_BUCKET,
                    Key=blake3_hash,
                    Expired=timedelta(days=7).total_seconds()
                ),
                result_type="jpeg",
                util_type="watermark"
            )
            return request_success(status_code=200)

        elif im.format == "PNG":
            change_to_tmp_dir()
            draw = ImageDraw.Draw(im)
            draw.text(xy=(width_pos, height_pos), text=text, fill="white", font=ImageFont.truetype(font, font_size))
            png_name = str(uuid.uuid4()) + '.png'
            im.save(png_name, "PNG")
            
            with open(png_name, "rb") as f:
                blake3_hash = blake3(f.read()).hexdigest()
            fput_util_result(png_name, blake3_hash, "watermark")

            os.remove(png_name)

            ImageUtilRecord.objects.create(
                user=user,
                result_url=client.get_presigned_url(
                    Method='GET',
                    Bucket=settings.WATERMARK_BUCKET,
                    Key=blake3_hash,
                    Expired=timedelta(days=7).total_seconds()
                ),
                result_type="png",
                util_type="watermark"
            )
            return request_success(status_code=200)
    
        else:
            raise TypeError("Unsupported image format.")
    
    else:
        return BAD_METHOD
    

@CheckRequire
def util_results(req: HttpRequest):
    if req.method == "GET":
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
        jw_token = auth[7:] # remove "Bearer " from the authorization header
        try:
            verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
            user = User.objects.filter(username=verification["username"]).first()
        except:
            return request_failed("Invalid digital signature", status_code=401)
        
        params = req.GET
        keywords = params.keys()

        if len(keywords) > 2:
            return request_failed("Too many query parameters", status_code=400)
        
        for keyword in keywords:
            if keyword not in ["page", "type"]:
                return request_failed("Invalid query parameters", status_code=400)
            
        page = require(params, "page", "int", err_msg="Missing or error type of [page]", strict=False)
        if page is None:
            page = 1

        type = require(params, "type", "string", err_msg="Missing or error type of [type]", strict=False)
        if type is None:
            type = "all"
        elif type not in ["convert", "resolution", "watermark"]:
            return request_failed("Invalid type", status_code=400)

        if type == "all":
            util_records = ImageUtilRecord.objects.filter(user=user).order_by("-finish_time")
        else:
            util_records = ImageUtilRecord.objects.filter(user=user, util_type=type).order_by("-finish_time")

        # Pagination
        record_pages = Paginator(util_records, UTIL_RESULT_PER_PAGE)
        util_result_cnt = record_pages.count
        util_result_page = record_pages.get_page(page)

        return request_success(
            {
                "count": util_result_cnt,
                "perPage": UTIL_RESULT_PER_PAGE,
                "result": [
                    {
                        "url": util_record.result_url,
                        "type": util_record.util_type,
                        "fileType": util_record.result_type,
                        "finishTime": util_record.finish_time,
                        "expiredTime": util_record.finish_time + util_record.expiry,
                    }
                for util_record in util_result_page],
            },
            status_code=200)

    else:
        return BAD_METHOD


@CheckRequire
def image_category(req: HttpRequest):
    if req.method == "GET":
        return request_success({"categories": [{"text": category["text"], "value": category["value"]} for category in IMAGE_CATEGORIES]}, status_code=200)
    else:
        return BAD_METHOD


@CheckRequire
def semiupload(req: HttpRequest):
    if req.method == "POST":
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
        jw_token = auth[7:] # remove "Bearer " from the authorization header
        body = json.loads(req.body.decode("utf-8").replace("'", '"'))
        try:
            verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
            uploader = User.objects.filter(username=verification["username"]).first()
        except:
            return request_failed("Invalid digital signature", status_code=401)
        
        hash = require(body, "hash", "string", "Missing or error type of [hash]")
        if AronaImage.objects.filter(hash=hash).exists():
            image = AronaImage.objects.filter(hash=hash).first()
            upload_image = AronaImage.objects.create(content_type=image.content_type, hash=hash, uploader=uploader, width=image.width, height=image.height)
            return request_success({"id": upload_image.id}, 200)
        else:
            return request_success(status_code=204)

    else:
        return BAD_METHOD


@CheckRequire
def upload_image(req: HttpRequest):
    if req.method == "POST":
        image = req.FILES.get("image", None)
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
        jw_token = auth[7:] # remove "Bearer " from the authorization header

        try:
            verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
            uploader = User.objects.filter(username=verification["username"]).first()
        except:
            return request_failed("Invalid digital signature", status_code=401)

        if image is None:
            return request_failed("Missing image", status_code=400)

        image_type = image.content_type.split('/')[-1]
        if image_type not in ["jpeg", "png", "gif"]:
            return request_failed("Invalid file type", status_code=400)
        if image_type == "gif":
            version = Image.open(image).info['version']
            if version == b'GIF87a': # GIF87a
                return request_failed("GIF87a is not supported", status_code=400)
        
        width, height = Image.open(image).size
        blake3_hash = blake3(image.read()).hexdigest()

        upload_image = AronaImage.objects.create(content_type=image_type, hash=blake3_hash, uploader=uploader, width=width, height=height)

        if image_type == "gif":
            change_to_tmp_dir()
            gif_name = str(uuid.uuid4()) + '.gif'
            with open(gif_name, "wb") as f:
                for chunk in image.chunks():
                    f.write(chunk)
            gif_name, webp_name = fput_object(gif_name, blake3_hash)

            os.remove(gif_name)
            os.remove(webp_name)

        elif image_type == "jpeg":
            change_to_tmp_dir()
            jpeg_name = str(uuid.uuid4()) + '.jpeg'
            with open(jpeg_name, "wb") as f:
                for chunk in image.chunks():
                    f.write(chunk)
            jpeg_name, webp_name = fput_object(jpeg_name, blake3_hash)

            os.remove(jpeg_name)
            os.remove(webp_name)

        elif image_type == "png":
            change_to_tmp_dir()
            png_name = str(uuid.uuid4()) + '.png'
            with open(png_name, "wb") as f:
                for chunk in image.chunks():
                    f.write(chunk)
            png_name, webp_name = fput_object(png_name, blake3_hash)

            os.remove(png_name)
            os.remove(webp_name)

        es_body = {
            "id": upload_image.id,
            "hash": upload_image.hash,
            "contentType": upload_image.content_type,
            "uploader": upload_image.uploader.username,
            "uploadTime": upload_image.upload_time,
            "likes": upload_image.likes,
            "comments": upload_image.comments,
            "width": upload_image.width,
            "height": upload_image.height,
            "title": upload_image.title,
            "tags": upload_image.tags,
            "description": upload_image.description,
            "category": upload_image.category,
        }
        url = "{}/{}/_doc".format(settings.ES_HOST, settings.ES_DB_NAME)
        headers = {"Content-Type": "application/json"}
        res = requests.post(url=url, headers=headers, data=json.dumps(es_body)).json()

        return request_success({"id": upload_image.id}, status_code=201)
        
    else:
        return BAD_METHOD
    

@CheckRequire
def download_image(req: HttpRequest, id: int):
    image_id = require({"id": id}, "id", "int", err_msg="Missing or error type of [id]")

    if req.method == "GET":
        params = req.GET
        keywords = params.keys()

        if len(keywords) > 1:
            return request_failed("Too many query parameters", status_code=400)

        if len(keywords) == 1:
            if "expiry" not in keywords:
                return request_failed("Missing query parameters", status_code=400)
            expiry = require(params, "expiry", "int", err_msg="Missing or error type of [expiry]")
        
        if len(keywords) == 0:
            expiry = 7

        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
        jw_token = auth[7:]

        try:
            verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
            downloader = User.objects.filter(username=verification["username"]).first()
        except:
            return request_failed("Invalid digital signature", status_code=401)
        
        image = AronaImage.objects.filter(id=image_id).first()
        if image is None:
            return request_failed("Image not found", status_code=404)
        
        if image.uploader != downloader:
            return request_failed("You are not the uploader", status_code=403)

        download_url = presigned_fget_object(image.content_type, image.hash, int(timedelta(days=expiry).total_seconds()))
        return request_success({"url": download_url}, status_code=200)
    
    else:
        return BAD_METHOD
    

@CheckRequire
def image(req: HttpRequest, hash: str):
    image_hash = require({"hash": hash}, "hash", "string", err_msg="Missing or error type of [hash]")

    if req.method == "GET":
        if not AronaImage.objects.filter(hash=image_hash).exists():
            return request_failed("Image not found", status_code=404)
        
        content_type = AronaImage.objects.filter(hash=image_hash).first().content_type
        if content_type == "gif":
            change_to_tmp_dir()
            gif_name = str(uuid.uuid4()) + '.gif'
            fget_object(gif_name, "gif", image_hash)

            with open(gif_name, "rb") as f:
                response = HttpResponse(f.read(), content_type="image/gif")
            os.remove(gif_name)
            return response
        
        elif content_type == "jpeg":
            change_to_tmp_dir()
            jpeg_name = str(uuid.uuid4()) + '.jpeg'
            fget_object(jpeg_name, "jpeg", image_hash)

            with open(jpeg_name, "rb") as f:
                response = HttpResponse(f.read(), content_type="image/jpeg")
            os.remove(jpeg_name)
            return response
        
        elif content_type == "png":
            change_to_tmp_dir()
            png_name = str(uuid.uuid4()) + '.png'
            fget_object(png_name, "png", image_hash)

            with open(png_name, "rb") as f:
                response = HttpResponse(f.read(), content_type="image/png")
            os.remove(png_name)
            return response

    else:
        return BAD_METHOD
    

@CheckRequire
def rough_image(req: HttpRequest, hash: str):
    image_hash = require({"hash": hash}, "hash", "string", err_msg="Missing or error type of [hash]")

    if req.method == "GET":
        if not AronaImage.objects.filter(hash=image_hash).exists():
            return request_failed("Image not found", status_code=404)
        
        content_type = AronaImage.objects.filter(hash=image_hash).first().content_type
        if content_type == "gif":
            change_to_tmp_dir()
            webp_name = str(uuid.uuid4()) + '.webp'
            fget_object(webp_name, "gif", image_hash, rough=True)
            
            with open(webp_name, "rb") as f:
                response = HttpResponse(f.read(), content_type="image/webp")
            os.remove(webp_name)
            return response
        
        elif content_type == "jpeg":
            change_to_tmp_dir()
            webp_name = str(uuid.uuid4()) + '.webp'
            fget_object(webp_name, "jpeg", image_hash, rough=True)

            with open(webp_name, "rb") as f:
                response = HttpResponse(f.read(), content_type="image/webp")
            os.remove(webp_name)
            return response
            
        elif content_type == "png":
            change_to_tmp_dir()
            webp_name = str(uuid.uuid4()) + '.webp'
            fget_object(webp_name, "png", image_hash, rough=True)

            with open(webp_name, "rb") as f:
                response = HttpResponse(f.read(), content_type="image/webp")
            os.remove(webp_name)
            return response

    else:
        return BAD_METHOD


@CheckRequire
def image_info(req: HttpRequest, id: int):
    image_id = require({"id": id}, "id", "int", err_msg="Missing or error type of [image id]")

    if req.method == "GET":
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]", strict=False)
        jw_token = auth[7:] if auth is not None else None

        if jw_token is not None:
            try:
                verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
                user = User.objects.filter(username=verification["username"]).first()
            except:
                return request_failed("Invalid digital signature", status_code=401)
            
        image = AronaImage.objects.filter(id=image_id).first()
        if image is None:
            return request_failed("Image not found", status_code=404)
        
        if jw_token is not None:
            AronaImageBrowseRecord.objects.create(image=image, browser=user)

        return request_success({
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
            "isLiked": False if jw_token is None else image.is_liked_by(user),
        }, status_code=200)
        
    elif req.method == "PATCH":
        body = json.loads(req.body.decode("utf-8").replace("'", '"'))
        title = require(body, "title", "string", err_msg="Missing or error type of [title]", strict=False)
        tags = require(body, "tags", "string", err_msg="Missing or error type of [tags]", strict=False)
        tags = re.findall(r"'(.*?)'", tags)
        description = require(body, "description", "string", err_msg="Missing or error type of [description]", strict=False)
        category = require(body, "category", "string", err_msg="Missing or error type of [category]", strict=False)
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
        jw_token = auth[7:] # remove "Bearer " from the authorization header

        try:
            verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
            updater = User.objects.filter(username=verification["username"]).first()
        except:
            return request_failed("Invalid digital signature", status_code=401)
        
        if not AronaImage.objects.filter(id=image_id).exists():
            return request_failed("Image not found", status_code=404)
        
        image_to_update = AronaImage.objects.filter(id=image_id).first()
        if updater != image_to_update.uploader:
            return request_failed("You are not the uploader of this image", status_code=403)
        
        if title is not None:
            image_to_update.title = title
                
            update_body = {
                "script": {
                    "source": "ctx._source.title = params.title",
                    "lang": "painless",
                    "params": {
                        "title": title
                    }
                }
            }
            es_id = get_es_id(image_id)
            headers = {"Content-Type": "application/json"}
            if es_id != "":
                url = "{}/{}/_update/{}".format(settings.ES_HOST, settings.ES_DB_NAME, es_id)
                res = requests.post(url, headers=headers, data=json.dumps(update_body)).json()

        if tags is not None:
            image_to_update.tags = tags

            update_body = {
                "script": {
                    "source": "ctx._source.tags = params.tags",
                    "lang": "painless",
                    "params": {
                        "tags": tags
                    }
                }
            }
            es_id = get_es_id(image_id)
            headers = {"Content-Type": "application/json"}
            if es_id != "":
                url = "{}/{}/_update/{}".format(settings.ES_HOST, settings.ES_DB_NAME, es_id)
                res = requests.post(url, headers=headers, data=json.dumps(update_body)).json()

        if description is not None:
            image_to_update.description = description

            update_body = {
                "script": {
                    "source": "ctx._source.description = params.description",
                    "lang": "painless",
                    "params": {
                        "description": description
                    }
                }
            }
            es_id = get_es_id(image_id)
            headers = {"Content-Type": "application/json"}
            if es_id != "":
                url = url = "{}/{}/_update/{}".format(settings.ES_HOST, settings.ES_DB_NAME, es_id)
                res = requests.post(url, headers=headers, data=json.dumps(update_body)).json()

        if category is not None:
            if category not in [category['value'] for category in IMAGE_CATEGORIES]:
                return request_failed("Invalid category", status_code=400)
            image_to_update.category = category

            update_body = {
                "script": {
                    "source": "ctx._source.category = params.category",
                    "lang": "painless",
                    "params": {
                        "category": category
                    }
                }
            }
            es_id = get_es_id(image_id)
            headers = {"Content-Type": "application/json"}
            if es_id != "":
                url = url = "{}/{}/_update/{}".format(settings.ES_HOST, settings.ES_DB_NAME, es_id)
                res = requests.post(url, headers=headers, data=json.dumps(update_body)).json()

        image_to_update.save()
        return request_success(status_code=200)

    elif req.method == "DELETE":
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]")
        jw_token = auth[7:] # remove "Bearer " from the auth

        try:
            verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
            deleter = User.objects.filter(username=verification["username"]).first()
        except:
            return request_failed("Invalid digital signature", status_code=401)
        
        if not AronaImage.objects.filter(id=image_id).exists():
            return request_failed("Image not found", status_code=404)
        
        image_to_delete = AronaImage.objects.filter(id=image_id).first()
        image_hash = image_to_delete.hash
        image_type = image_to_delete.content_type

        if deleter != image_to_delete.uploader:
            return request_failed("You are not the uploader of this image", status_code=403)
        
        image_to_delete.delete()
        if not AronaImage.objects.filter(hash=image_hash).exists():
            if image_type == "gif":
                client.delete_object(Bucket=settings.GIF_BUCKET, Key=f"{image_hash}.gif")
                client.delete_object(Bucket=settings.ROUGH_GIF_BUCKET, Key=f"{image_hash}.webp")
            elif image_type == "jpeg":
                client.delete_object(Bucket=settings.JPEG_BUCKET, Key=f"{image_hash}.jpeg")
                client.delete_object(Bucket=settings.ROUGH_JPEG_BUCKET, Key=f"{image_hash}.webp")
            elif image_type == "png":
                client.delete_object(Bucket=settings.PNG_BUCKET, Key=f"{image_hash}.png")
                client.delete_object(Bucket=settings.ROUGH_PNG_BUCKET, Key=f"{image_hash}.webp")

        es_id = get_es_id(image_id)
        url = "{}/{}/_doc/{}".format(settings.ES_HOST, settings.ES_DB_NAME, es_id)
        headers = {"Content-Type": "application/json"}
        res = requests.delete(url, headers=headers).json()

        return request_success(status_code=200)

    else:
        return BAD_METHOD


@CheckRequire
def image_comments(req: HttpRequest, id: int):
    image_id = require({"id": id}, "id", "int", err_msg="Missing or error type of [image id]")

    if req.method == "GET":
        params = req.GET
        keywords = params.keys()
        auth = require(req.headers, "authorization", "string", err_msg="Missing or error type of [authorization]", strict=False)
        jw_token = auth[7:] if auth is not None else None

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
        
        image = AronaImage.objects.filter(id=image_id).first()
        if image is None:
            return request_failed("Image not found", status_code=404)

        if jw_token is not None:
            try:
                verification = jwt.decode(jw_token, settings.EDDSA_PUBLIC_KEY, algorithms="EdDSA")
                user = User.objects.filter(username=verification["username"]).first()
            except:
                return request_failed("Invalid digital signature", status_code=401)

        comments = Comment.objects.filter(belong_to_image=image)

        # Get the first level comments
        if sorted_by == "time":
            first_level_comments = comments.filter(belong_to_comment=None).order_by("-post_time")
        second_level_comments = comments.exclude(belong_to_comment=None).order_by("post_time")

        # Pagination
        comment_pages = Paginator(first_level_comments, COMMENT_PER_PAGE)
        comment_cnt = comment_pages.count
        result_page = comment_pages.get_page(page)

        # Construct the two-layer comment list
        comment_list = []
        for comment in result_page:
            comment_list.append({
                "id": comment.id,
                "content": comment.content,
                "poster": {
                    "username": comment.poster.username,
                    "nickname": comment.poster.nickname,
                    "registerTime": comment.poster.registerTime,
                    "userType": comment.poster.userType,
                    "slogan": comment.poster.slogan,
                    "email": comment.poster.email,
                },
                "postTime": comment.post_time,
                "likes": comment.likes,
                "comments": comment.comments,
                "isLiked": False if jw_token is None else comment.is_liked_by(user),
                "replies": [],
            })

            sub_comments = second_level_comments.filter(belong_to_comment=comment).order_by("post_time")
            for sub_comment in sub_comments:
                comment_list[-1]["replies"].append({
                    "id": sub_comment.id,
                    "content": sub_comment.content,
                    "poster": {
                        "username": comment.poster.username,
                        "nickname": comment.poster.nickname,
                        "registerTime": comment.poster.registerTime,
                        "userType": comment.poster.userType,
                        "slogan": comment.poster.slogan,
                        "email": comment.poster.email,
                    },
                    "postTime": sub_comment.post_time,
                    "likes": sub_comment.likes,
                    "replyToUser": sub_comment.reply_to_user_username,
                    "isLiked": False if jw_token is None else sub_comment.is_liked_by(user),
                })

        return request_success(
            {
                "count": comment_cnt,
                "perPage": COMMENT_PER_PAGE,
                "result": comment_list,
            },
            status_code=200)

    else:
        return BAD_METHOD
