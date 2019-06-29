from django.http import HttpResponse
from django.shortcuts import render
from rest_framework.views import APIView
from meidou_mall.libs.captcha.captcha import captcha
from django_redis import get_redis_connection

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