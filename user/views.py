from django.shortcuts import render

# Create your views here.
import json
import os.path
import pprint
import time
import uuid
import platform
from django.contrib.auth.models import AnonymousUser
import jwt
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
import re
from datetime import datetime, timedelta
from django.template import loader
from jose import JWTError
from jwt import ExpiredSignatureError

from summer_backend import settings
from summer_backend.settings import SECRET_KEY, EMAIL_HOST_USER
from team.models import Member, Team
from user.authentication import validate_all, validate_login
from user.cos_utils import get_cos_client, Label, Category, SubLabel
from user.models import User
from django.utils import timezone


# Create your views here.
@validate_all
def register(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    username = request.POST.get('username')
    nickname=request.POST.get('nickname')
    pswd1 = request.POST.get('password1')
    pswd2 = request.POST.get('password2')
    email = request.POST.get('email')
    avatar = request.FILES.get('avatar')
    pswd_pattern = r'^(?=.*\d)(?=.*[a-zA-Z])[a-zA-Z\d]{8,16}$'
    email_pattern = r'^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if nickname is None:
        return JsonResponse({'errno': 1, 'msg': "昵称为空"})
    if not username or len(username) > 10:
        return JsonResponse({'errno': 1, 'msg': "用户名长度不合法！"})
    if not pswd2 == pswd1:
        return JsonResponse({'errno': 1, 'msg': "两次输入密码不一致！"})
    elif not re.match(pswd_pattern, pswd1):
        return JsonResponse({'errno': 1, 'msg': "密码格式必须为：8-16位且包含数字和字母"})
    if not re.match(email_pattern, email):
        return JsonResponse({'errno': 1, 'msg': "邮箱格式不合法"})
    user_list = User.objects.filter(email=email)
    user = user_list.last()
    user_count = user_list.count()
    if user_count >= 1:  # 只保留最后一个，其他全都删掉
        user_list.exclude(pk=user.pk).delete()
        if user.is_active:
            return JsonResponse({'errno': 1, 'msg': "该用户已注册"})
        else:
            now_time = timezone.now()
            if (now_time - user.created_at).seconds <= 300:
                return JsonResponse({'errno': 1, 'msg': "注册时间间隔需大于5min"})
    user = User.objects.create(username=username, password=pswd1, email=email,current_team_id=0)
    if avatar:
        res, avatar_url, content = upload_cover_method(avatar, user.id, 'user_avatar')
        if res == -2:
            return JsonResponse({'errno': 1, 'msg': "图片格式不合法"})
        elif res == 1:
            return JsonResponse({'errno': 1, 'msg': content})
        else:
            user.avatar_url = avatar_url
    user.save()
    payload = {"user_id": user.id, 'email': email, "timestamp": int(time.time())}
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    send_status, url = send_email(email, token, "register")
    if send_status:
        return JsonResponse({'errno': 0, 'msg': "邮件成功发送", })
    else:
        return JsonResponse({'errno': 1, 'msg': "邮件发送失败"})


def send_email(email, token, type):
    # payload={"user_id":user_id,'email':email}
    # token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    if platform.system() == "Linux":
        url = "http://www.aamofe.top/api/user/activate/" + token
    else:
        url = "http://127.0.0.1/api/user/activate/" + token
    data = {'url': url}
    email_title = email_body = ''
    if type == 'register':
        email_title = r'欢迎注册'
        email_body = loader.render_to_string('register.html', data)
    try:
        msg = EmailMessage(email_title, email_body, EMAIL_HOST_USER, [email])
        msg.content_subtype = 'html'
        send_status = msg.send()
        return send_status, url
    except:
        return False


@validate_all
def activate(request, token):
    payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    user_id = payload.get('user_id')
    timestamp = payload.get('timestamp')
    context = {'title': '链接已过期', 'message': '激活链接已过期，请重新注册',
               'url': 'http://www.aamofe.top/api/user/register'}
    current_time = int(time.time())
    if current_time - timestamp > 5 * 60:
        return render(request, 'activate.html', context)
    try:
        user = User.objects.get(id=user_id)
        email = payload.get('email')
        if not email:
            title = '邮箱不正确'
            message = '邮箱不存在，信息有误，请重新注册'
        else:
            user.is_active = True
            user.save()
            title = '激活成功'
            message = '欢迎登录'
            url = 'http://www.aamofe.top/'
            team=Team.objects.create(name="个人空间",user=user)
            user.current_team_id=team.id
            user.save()
    except:
        title = '激活失败'
        message = '该邮箱已注册，请更换邮箱重新注册'
        url = 'http://www.aamofe.top/api/user/register'
    context['title'] = title
    context['message'] = message
    context['url'] = url
    return render(request, 'activate.html', context)


@validate_all
def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            user = User.objects.get(email=email, password=password, is_active=True)
        except User.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "用户不存在！"})
        payload = {'exp': datetime.utcnow() + timedelta(days=5), 'id': user.id}
        encode = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        token = str(encode)
        user_info={'user_id': user.id,'current_team':user.current_team_id,'token':token}
        return JsonResponse({ 'user_info':user_info, 'errno': 0, 'msg': "登录成功"})
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})

@validate_login
def logout(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    request.session.flush()
    return JsonResponse({'errno': 0, 'msg': "登出成功"})

@validate_login
def update_info(request):
    if request.method == 'POST':
        user = request.user
        nickname = request.POST.get('nickname')
        password = request.POST.get('password')
        avatar = request.FILES.get('avatar')
        if nickname:
            user.nickname = nickname
        if password:
            user.password = password
        if avatar:
            res, avatar_url, content = upload_cover_method(avatar, user.id, 'user_avatar')
            if res == -2:
                return JsonResponse({'errno': 1, 'msg': "图片格式不合法"})
            elif res == 1:
                return JsonResponse({'errno': 1, 'msg': content})
            else:
                user.avatar_url = avatar_url
        user.save()
        return JsonResponse({'errno': 0, 'msg': "修改信息成功"})
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})

# 修改个人信息：nickname，密码
def upload_cover_method(cover_file, cover_id, url):
    client, bucket_name, bucket_region = get_cos_client()
    if cover_id == '' or cover_id == 0:
        cover_id = str(uuid.uuid4())
    file_name = cover_file.name
    file_extension = file_name.split('.')[-1]  # 获取文件后缀
    if file_extension == 'jpg':
        ContentType = "image/jpg"
    elif file_extension == 'jpeg':
        ContentType = "image/jpeg"
    elif file_extension == 'png':
        ContentType = "image/png"
    else:
        return -2, None, None
    cover_key = f"{url}/{cover_id}.{file_extension}"
    response_cover = client.put_object(
        Bucket=bucket_name,
        Body=cover_file,
        Key=cover_key,
        StorageClass='STANDARD',
        ContentType=ContentType
    )
    if 'url' in response_cover:
        cover_url = response_cover['url']
    else:
        cover_url = f'https://{bucket_name}.cos.{bucket_region}.myqcloud.com/{cover_key}'
    response_submit = client.get_object_sensitive_content_recognition(
        Bucket=bucket_name,
        BizType='aa3bbd2417d7fa61b38470534735ff20',
        Key=cover_key,
    )
    res = int(response_submit['Result'])
    Score = int(response_submit['Score'])
    if res == 1 or res == 2 or Score >= 60:
        category = response_submit['Category']
        label = response_submit['Label']
        subLabel = response_submit['SubLabel']
        if label == 'Politics':
            content = "您的视频封面被判定为违规！" + \
                      "标签是" + Label[label] + "，具体内容是：" + response_submit['PoliticsInfo']['Label'] + \
                      "。判定比例高达 " + str(Score) + "%。请修改"
        else:
            content = "您的视频封面被判定为违规！" + \
                      "标签是：" + Label[label] + "，分类为：" + Category[category] + "，具体内容是" + SubLabel[subLabel] + \
                      "。判定比例高达" + str(Score) + "%。请修改！"
        delete_cover_method(url, cover_id, file_extension)
        return 1, None, content
    return res, cover_url, None
def delete_cover_method(url, cover_id, file_extension):
    client, bucket_name, bucket_region = get_cos_client()
    cover_key = f"{url}/{cover_id}.{file_extension}"
    response = client.delete_object(
        Bucket=bucket_name,
        Key=cover_key
    )


def delete_video_method(video_id):
    client, bucket_name, bucket_region = get_cos_client()
    video_key = "video_file/{}".format(f'{video_id}.mp4')
    response = client.delete_object(
        Bucket=bucket_name,
        Key=video_key
    )
    pprint.pprint(response)


def upload_video_method(video_file, video_id, ):
    client, bucket_name, bucket_region = get_cos_client()
    if video_id == '' or video_id == 0:
        video_id = str(uuid.uuid4())
    file_name = video_file.name
    file_extension = file_name.split('.')[-1]  # 获取文件后缀
    print("ex :", file_extension)
    if file_extension != 'mp4':
        return 1
    video_key = "video_file/{}".format(f'{video_id}.mp4')
    response_video = client.put_object(
        Bucket=bucket_name,
        Body=video_file,
        Key=video_key,
        StorageClass='STANDARD',
        ContentType="video/mp4"
    )
    return 0


def call_back(request):
    if request.method == 'POST':
        body = json.loads(request.body)
        code = body.get("code")  # 错误码，值为0时表示审核成功，非0表示审核失败
        data = body.get("data")  # 视频审核结果的详细信息。
        JobId = data.get("trace_id")
        url = data.get("url")
        result = int(data.get("result"))
        porn_info = data.get("porn_info")  # 审核场景为涉黄的审核结果信息。
        ads_info = data.get("ads_info")
        terrorist_info = data.get("terrorist_info")
        politics_info = data.get("'politics_info")
        if ads_info.get("hit_flag") != 0:
            score = ads_info.get("score")
            content = "您的视频被判定为违规！" + "标签是:广告元素，" + "判定比例高达 " + str(score) + "%，"
        elif porn_info.get("hit_flag") != 0:
            score = porn_info.get("score")
            content = "您的视频被判定为违规！" + "标签是:涉黄元素，" + "判定比例高达 " + str(score) + "%，"
        elif politics_info.get("hit_flag") != 0:
            score = politics_info.get("score")
            content = "您的视频被判定为违规！" + "标签是:政治元素，" + "判定比例高达 " + str(score) + "%，"
        elif terrorist_info.get("hit_flag") != 0:
            score = terrorist_info.get("score")
            content = "您的视频被判定为违规！" + "标签是:暴力元素，" + "判定比例高达 " + str(score) + "%，"
        video_id = re.search(r'\d+(?=\.\w+$)', url).group()
        return JsonResponse({'errno': 1, 'result': result})

@validate_all
def show_info(request, id):
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user=request.user
    if isinstance(user, AnonymousUser):
        is_login = False
    else :
        is_login=True
    print("is_login : ",is_login)
    if id==0 and not is_login:
        return JsonResponse({'errno': 1, 'msg': "未登录"})
    if id!=0:
        try:
            user = User.objects.get(id=id, is_active=True)
        except User.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "查看对象不存在"})
    # print('isLogin :',is_login)
    user_info = user.to_dict()
    # pprint.pprint(user_info)
    return JsonResponse({'errno': 0, 'msg': "查看信息成功", 'user_info': user_info})
@validate_login
def personal_info(request):
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user=request.user
    user_info = user.to_dict()
    # pprint.pprint(user_info)
    return JsonResponse({'errno': 0, 'msg': "查看信息成功", 'user_info': user_info})
