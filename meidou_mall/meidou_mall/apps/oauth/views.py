from django.shortcuts import render

# Create your views here.
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_jwt.settings import api_settings

from carts.utils import merge_cart_cookie_to_redis
from oauth.models import OAuthQQUser
from oauth.serializers import OAuthQQUserSerializer
from oauth.utils import OAuthQQ
from .exceptions import OAuthQQAPIError


#  url(r'^qq/authorization/$', views.QQAuthURLView.as_view()),
class QQAuthURLView(APIView):
    """获取qq登录的url"""    # ?next=xxxx
    def get(self, request):
        """提供用于qq登录的url"""
        # 获取next参数
        next = request.query_params.get('next')

        # 拼接qq登录的网址
        oauth_qq = OAuthQQ(state=next)
        login_url = oauth_qq.get_login_url()
        # print("login_url: %s" % login_url)

        return Response({'login_url': login_url})


class QQAuthUserView(CreateAPIView):
    """qq登录的用户"""    # ?code=xxxx
    serializer_class = OAuthQQUserSerializer

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
            return Response({'message': '访问QQ接口异常'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # 根据openid查询数据库OAuthQQUser 判断数据是否存在
        try:
            oauth_qq_user = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:
            # 如果数据不存在.处理openid 并返回
            openid_token = oauth_qq.generate_bind_user_access_token(openid)
            return Response({'access_token': openid_token})
        else:
            # 如果数据存在,表示用户已经绑定多身份,签发JWT token
            jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
            jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

            user = oauth_qq_user.user
            payload = jwt_payload_handler(user)
            token = jwt_encode_handler(payload)

            # return Response({
            #     'username': user.username,
            #     'user_id': user.id,
            #     'token': token
            # })
            response = Response({
                'username': user.username,
                'user_id': user.id,
                'token': token
            })

            # 合并购物车
            response = merge_cart_cookie_to_redis(request, user, response)

            return response

    def post(self, request, *args, **kwargs):
        # post方法中的创建用户绑定逻辑，还是由super处理。由super调用序列化器的create方法
        # 因一登录就要合并购物车,故重写此方法
        response = super().post(request, *args, **kwargs)

        # 合并购物车
        user = self.user   # 序列化器中已添加了一个user属性
        response = merge_cart_cookie_to_redis(request, user, response
                                              )
        return response