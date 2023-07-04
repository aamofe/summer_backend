import os.path
import pprint

import jwt
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.shortcuts import render
import re

from django.template import loader

from Summer_Backend.settings import SECRET_KEY, EMAIL_HOST_USER
from user.models import User
# Create your views here.
def register(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方式错误！"})
    username=request.POST.get('username')
    pswd1=request.POST.get('password1')
    pswd2=request.POST.get('password2')
    email=request.POST.get('email')
    pswd_pattern = r'^(?=.*\d)(?=.*[a-zA-Z])[a-zA-Z\d]{8,16}$'
    email_pattern = r'^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not username or len(username)>10:
        return JsonResponse({'errno': 1, 'msg': "用户名长度不合法！"})
    if not pswd2==pswd1:
        return JsonResponse({'errno': 1, 'msg': "两次输入密码不一致！"})
    elif not re.match(pswd_pattern,pswd1):
        return JsonResponse({'errno': 1, 'msg': "密码格式必须为：8-16位且包含数字和字母"})
    if not re.match(email_pattern,email):
        return JsonResponse({'errno': 1, 'msg': "邮箱格式不合法"})
    user=User.objects.create(username=username,password=pswd1,email=email)
    send_status=send_email(user.id,email,"activate")
    if send_status:
        return JsonResponse({'errno': 0, 'msg': "邮件成功发送"})
    else:
        return JsonResponse({'errno': 1, 'msg': "邮件发送失败"})
def send_email(user_id,email,type):
    payload={"user_id":user_id,'email':email}
    token=jwt.encode(payload,SECRET_KEY)
    url=os.path.join("http://www.aamofe.top/api/user/activate/",token)#测试用
    data={'url':url}
    email_title=email_body=''
    if type=='activate':
        email_title=r'欢迎注册'
        email_body=loader.render_to_string('register.html',data)
    elif type=='find':
        email_title=r'重设密码'
        email_body = loader.render_to_string('find_pswd.html', data)
    try:
        msg=EmailMessage(email_title,email_body,EMAIL_HOST_USER,[email])
        msg.content_subtype='html'
        send_status=msg.send()
        return send_status
    except :
        return False
def activate(request,token):
    payload=jwt.decode(token,SECRET_KEY)
    user_id=payload.get('user_id')
    context={'url':'','title':'','message':''}
    try:
        user=User.objects.get(id=user_id)
        email = payload.get('email')
        if not email:
            title = '邮箱不正确'
            message = '邮箱不存在，信息有误，请重新注册'
            url='http://www.aamofe.top/api/user/register'
        else:
            user.isActive = True
            user.save()
            title = '注册成功'
            message = '欢迎注册'
            url = 'http://www.aamofe.top/'
    except:
        title='激活失败'
        message='该邮箱已注册，请更换邮箱重新注册'
        url = 'http://www.aamofe.top/api/user/register'
    context['title']=title
    context['message']=message
    context['url']=url
    pprint.pprint(context)
    return render(request, 'activate.html', context)
def login(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方式错误！"})
    username=request.POST.get('username')
def logout(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方式错误！"})
    username=request.POST.get('username')
def get_information(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方式错误！"})
    username=request.POST.get('username')