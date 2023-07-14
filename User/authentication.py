from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions

from .utils import decode_jwt_token

class JWTAuthentication(BaseAuthentication):
    
    def authenticate(self, request):
        token = request.META.get('HTTP_AUTHORIZATION') 
        if not token:
            return None
        
        try:
            user = decode_jwt_token(token)
        except:
            raise exceptions.AuthenticationFailed()
        
        return (user, None)