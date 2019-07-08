from django.shortcuts import render

# Create your views here.
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import mixins
from rest_framework.viewsets import GenericViewSet

from users import constants
from users.models import User
from users.serializers import CreateUserSerializer, UserDetailSerializer, EmailSerializer, UserAddressSerializer, AddressTitleSerializer


class UsernameCountView(APIView):
    '''用户名数量,用于判断用户名是否已存在'''
    # 因逻辑本身比较简单,用GenericAPIView的话还需要定义序列化器,故直接继承APIView
    def get(self, request, username):
        '''获取指定用数量 '''
        count = User.objects.filter(username=username).count()
        data = {
            'username': username,
            'count': count
        }
        return Response(data)



class MobileCountView(APIView):
    '''手机号数量,用于判断手机号是否已经注册过'''
    def get(self, request, mobile):
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


# GET /user/
class UserDetailView(RetrieveAPIView):
    '''用户基本信息'''
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]  # 指明必须登录认证后才能访问

    # 在RetrieveAPIView中获取详情数据的url是/user/<pk>,而现在设计的接口是/user/
    # 故只能重写get_object方法
    def get_object(self):
        # 返回当前请求的用户
        # 在类视图对象中,可以通过类视图对象的属性获取request
        # 在django的请求request对象中,user属性表明当前请求的用户
        return self.request.user


# PUT /email/
class EmailView(UpdateAPIView):
    serializer_class = EmailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class VerifyEmailView(APIView):
    """邮箱验证"""
    def get(self, request):
        # 获取token
        token = request.query_params.get('token')
        if not token:
            return Response({'message': '缺少token'}, status=status.HTTP_400_BAD_REQUEST)

        # 验证token
        user = User.check_verify_email_token(token)
        if user is None:
            return Response({'message': '链接信息无效'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            user.email_active = True
            user.save()
            return Response({'message': 'OK'})


class AddressViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, GenericViewSet):
    '''用户地址新增与修改'''
    serializer_class = UserAddressSerializer
    permissions = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.addresses.filter(is_deleted=False)

    def list(self, request, *args, **kwargs):
        '''用户地址列表数据'''
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        user = self.request.user
        return Response({
            'user_id': user.id,
            'default_address_id': user.default_address_id,
            'limit': constants.USER_ADDRESS_COUNTS_LIMIT,
            'addresses': serializer.data,
        })

    def create(self, request, *args, **kwargs):
        '''保存用户地址数据'''
        # 检查用户地址数据数目不能超过上限
        count = request.user.addresses.filter(is_deleted=False).count()
        if count >= constants.USER_ADDRESS_COUNTS_LIMIT:
            return Response({'message': '保存地址数据已达到上限'}, status=status.HTTP_400_BAD_REQUEST)

        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        '''处理删除'''
        address = self.get_object()
        # 进行逻辑删除
        address.is_deleted = True
        address.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['put'], detail=True)
    def status(self, request, pk=None, address_id=None):
        '''设置默认地址'''
        address = self.get_object()
        request.user.default_address = address
        request.user.save()
        return Response({'message': 'OK'}, status=status.HTTP_200_OK)

    @action(methods=['put'], detail=True)
    def title(self, request, pk=None, address_id=None):
        '''修改标题'''
        address = self.get_object()
        serializer = AddressTitleSerializer(instance=address, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
























