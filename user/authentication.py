from django.http import JsonResponse
from django.shortcuts import redirect
from jose import jwt, ExpiredSignatureError, JWTError
from django.conf import settings
from user.models import User


# 必须是已登录状态
def validate_login(func):
    def valid_per(request, *args, **kwargs):
        token = request.META.get('HTTP_Authorization'.upper())
        if not token:
            return redirect('http://www.aamofe.top/api/user/register/')
        token = token.replace('Bearer ', '')
        try:
            jwt_token = jwt.decode(token, settings.SECRET_KEY, options={'verify_signature': False})
        except ExpiredSignatureError:
            return JsonResponse({'errno': 401, 'msg': "登录已过期，请重新登录"})
        except JWTError:
            return JsonResponse({'errno': 401, 'msg': "用户未登录，请先登录"})
        try:
            user = User.objects.get(id=jwt_token.get('id'))
        except User.DoesNotExist:
            return JsonResponse({'errno': 401, 'msg': "用户不存在，请先注册"})
        request.user = user
        return func(request, *args, **kwargs)

    return valid_per


# 游客/已登录用户都可访问
def validate_all(func):
    def valid_per(request, *args, **kwargs):
        token = request.META.get('HTTP_Authorization'.upper())
        if token:
            token = token.replace('Bearer ', '')
            try:
                jwt_token = jwt.decode(token, settings.SECRET_KEY)
            except ExpiredSignatureError:
                return JsonResponse({'errno': 401, 'msg': "登录已过期，请重新登录"})
            except JWTError:
                return JsonResponse({'errno': 401, 'msg': "用户未登录，请先登录"})
            try:
                user = User.objects.get(id=jwt_token.get('id'))
            except User.DoesNotExist:
                return JsonResponse({'errno': 401, 'msg': "用户不存在，请先注册"})
            request.user = user
        return func(request, *args, **kwargs)
    return valid_per
