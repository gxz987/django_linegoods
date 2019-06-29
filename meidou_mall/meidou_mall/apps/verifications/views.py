from django.shortcuts import render
from rest_framework.views import APIView

# Create your views here.


class ImageCodeView(APIView):
    '''图片验证码'''
    # 这个视图逻辑，不需要校验参数，因为这个参数由url路由中的正则就可以校验,故继承APIview即可
    def get(self, request, image_code_id):
        # 生成验证码图片
        # 保存真实值
        # 返回图片
        pass