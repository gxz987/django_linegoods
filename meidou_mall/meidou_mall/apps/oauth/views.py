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

        oauth_qq = OAuthQQ()
        try:
            # 根据code 获取access_token
            access_token = oauth_qq.get_access_token(code)
            # 根据access_token 获取openid
            openid = oauth_qq.get_openid(access_token)
        except OAuthQQAPIError:
            return Response({'message': '获取access_token失败'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


        # 根据openid查询数据库OAuthQQUser 判断数据是否存在

        # 如果数据存在,表示用户已经绑定多身份,签发JWT token

        # 如果数据不存在.处理openid 并返回