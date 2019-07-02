from django.shortcuts import render

# Create your views here.
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User
from users.serializers import CreateUserSerializer


class UsernameCountView(APIView):
    print(111)
    '''用户名数量,用于判断用户名是否已存在'''
    # 因逻辑本身比较简单,用GenericAPIView的话还需要定义序列化器,故直接继承APIView
    def get(self, request, username):
        print(1)
        '''获取指定用数量 '''
        count = User.objects.filter(username=username).count()
        data = {
            'username': username,
            'count': count
        }
        return Response(data)



class MobileCountView(APIView):
    print(187)
    '''手机号数量,用于判断手机号是否已经注册过'''
    def get(self, request, mobile):
        print(8888)
        '''获取指定手机号数量 '''
        count = User.objects.filter(mobile=mobile).count()
        data = {
            'mobile': mobile,
            'count': count
        }

        return Response(data)


class UserView(CreateAPIView):
    '''
    用户注册
    传入参数:
        username, password, password2, sms_code, mobile, allow
    '''
    # 接收参数

    # 校验参数

    # 保存用户数据,密码加密

    # 序列化 返回数据
    serializer_class = CreateUserSerializer



