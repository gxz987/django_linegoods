from django.shortcuts import render

# Create your views here.
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from oauth.utils import OAuthQQ
from .exceptions import OAuthQQAPIError

#  url(r'^qq/authorization/$', views.QQAuthURLView.as_view()),
class QQAuthURLView(APIView):
    """获取qq登录的url"""
    def get(self, request):
        """提供用于qq登录的url"""
        # 获取next参数
        next = request.query_params.get('next')

        # 拼接qq登录的网址
        oauth_qq = OAuthQQ(state=next)
        login_url = oauth_qq.get_login_url()

        return Response({'login_url': login_url})


class QQAuthUserView(APIView):
    """qq登录的用户"""
    def get(self, request):
        # 获取code
        code = request.query_params.get('code')
        if not code:
            return Response({'message': '缺少code'}, status=status.HTTP_400_BAD_REQUEST)

        # 根据code 获取access_token
        oauth_qq = OAuthQQ()
        try:
            access_token = oauth_qq.get_access_token(code)
        except OAuthQQAPIError:
            return Response()