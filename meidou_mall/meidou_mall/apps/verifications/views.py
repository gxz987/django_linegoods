from django.http import HttpResponse
from django.shortcuts import render
from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView
from meidou_mall.libs.captcha.captcha import captcha
from django_redis import get_redis_connection

from verifications.serializer import ImageCodeCheckSerializer
from . import constants

# Create your views here.


class ImageCodeView(APIView):
    '''图片验证码'''
    # 这个视图逻辑，不需要校验参数，因为这个参数由url路由中的正则就可以校验,故继承APIview即可
    def get(self, request, image_code_id):

        # 生成验证码图片
        text, image = captcha.generate_captcha()

        # 保存真实值
        redis_conn = get_redis_connection('verify_codes')
        redis_conn.setex("img_%s" % image_code_id, constants.IMAGE_CODE_REDIS_EXPIRES, text)

        # 固定返回验证码图片数据，不需要REST framework框架的Response帮助我们决定返回响应数据的格式
        # 所以此处直接使用Django原生的HttpResponse即可
        return HttpResponse(image, content_type="images/jpg")


# url('^/sms_codes/(?P<mobile>1[3-9]\d{9})/$', views.SMSCodeView.as_view()),
class SMSCodeView(GenericAPIView):
    """短信验证码"""
    # 传入参数:mobile, image_code_id, text

    serializer_class = ImageCodeCheckSerializer
    def get(self):
        # 校验参数, 由序列化器完成

        # 生成短信验证码

        # 保存短信验证码  发送记录

        # 发送短信

        # 返回数据
        pass