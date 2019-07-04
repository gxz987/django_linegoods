from django.shortcuts import render

# Create your views here.
from rest_framework.response import Response
from rest_framework.views import APIView

from oauth.utils import OAuthQQ


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