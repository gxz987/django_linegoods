import random

from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView
from meidou_mall.libs.captcha.captcha import captcha
from django_redis import get_redis_connection
import logging

from verifications.serializer import ImageCodeCheckSerializer
from . import constants

# Create your views here.

logger = logging.getLogger('django')


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
    def get(self, request, mobile):
        # 校验参数, 由序列化器完成
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        # 生成短信验证码
        sms_code = '%06d' % random.randint(0, 999999)

        # 保存短信验证码  发送记录
        redis_conn = get_redis_connection('verify_code')
        # redis_conn.setex("sms_%s" % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        # redis_conn.setex("send_flag_%s" % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)

        # redis管道
        pl = redis_conn.pipeline()
        pl.setex("sms_%s" % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        pl.setex("sms_flag_%s" % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)

        # 让管道通知redis执行命令
        pl.execute()

        # 发送短信
        from meidou_mall.meidou_mall.utils.yuntongxun.sms import CCP

        try:
            ccp = CCP()
            expires = constants.SMS_CODE_REDIS_EXPIRES // 60
            result = ccp.send_template_sms(mobile, [sms_code, expires], constants.SMS_CODE_TEMP_ID)
        except Exception as e:
            logger.error('发送短信验证码[异常][ mobile: %s, message: %s]' % (mobile, e))
            return Response({'message': 'failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            if result == 0:
                logger.info('发送短信验证码[正常][ mobile: %s]' % mobile)
                return Response({'message': 'OK'})
            else:
                logger.warning('发送短信验证码[失败][ mobile: %s ]' % mobile)
                return Response({'message': 'failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

