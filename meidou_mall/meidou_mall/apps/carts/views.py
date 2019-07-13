from django.shortcuts import render
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
import pickle
import base64

from . import constants
from .serializers import CartSerializer, CartSKUSerializer, CartDeleteSerializer
from goods.models import SKU
# Create your views here.


class CartView(GenericAPIView):
    """购物车"""
    serializer_class = CartSerializer

    def perform_authentication(self, request):
        """将执行具体请求方法前的身份认证关掉，由视图自己来进行身份认证"""
        pass

    def post(self, request):
        """保存购物车"""
        # sku_id  count  selected
        # 校验
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sku_id = serializer.validated_data['sku_id']
        count = serializer.validated_data['count']
        selected = serializer.validated_data['selected']

        # 判断用户登录状态
        try:
            user = request.user   # 匿名用户 AnonymoseUser
        except Exception:
            user = None

        # 保存
        if user and user.is_authenticated:
            # 如果用户已登录，保存到redis
            redis_conn = get_redis_connection('cart')
            pl = redis_conn.pipeline()  # 管道

            # 用户购物车数据  redis hash哈希
            # 哈希的hincrby方法：若以前有就在原先基础上累加，若以前没有就添加
            pl.hincrby('cart_%s' % user.id, sku_id, count)

            # 用户购物车勾选数据  redis  set
            if selected:
                pl.sadd('cart_selected_%s' % user.id, sku_id)

            pl.execute()  # 管道执行
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        else:
            # 如果用户未登录，保存到cookie  reponse = Response() response.set_cookie
            # 取出cookie中的购物车数据
            cart_str = request.COOKIES.get('cart')

            if cart_str:
                # 解析
                cart_bytes = cart_str.encode()  # str -> bytes
                cart_bytes = base64.b64decode(cart_bytes)  # b64decode(byes类型）
                cart_dict = pickle.loads(cart_bytes)
            else:
                cart_dict = {}

            # cart_dict = {
            #     sku_id_1: {
            #         'count': 10
            #         'selected': True
            #     },
            #     sku_id_2: {
            #         'count': 10
            #         'selected': False
            #     },
            #     sku_id_3: {
            #         'count': 10
            #         'selected': True
            #     }
            # }

            if sku_id in cart_dict:
                # 如果商品存在购物车中，累加
                cart_dict[sku_id]['count'] += count
                cart_dict[sku_id]['selected'] = selected
            else:
                # 如果商品不在购物车中，设置
                cart_dict[sku_id] = {
                    'count': count,
                    'selected': selected
                }

            cart_cookie = base64.b64encode(pickle.dumps(cart_dict)).decode()

            # 设置cookie
            response = Response(serializer.data, status=status.HTTP_201_CREATED)
            response.set_cookie('cart', cart_cookie, max_age=constants.CART_COOKIE_EXPIRES)

            return response

    def get(self, request):
        '''查询购物车'''

        # 判断用户的登录状态
        try:
            user = request.user
        except Exception:
            user = None

        # 查询
        if user and user.is_authenticated:
            # 如果用户已登录,从redis查询,  sku_id  count  selected
            redis_conn = get_redis_connection('cart')
            redis_cart = redis_conn.hgetall('cart_%s' % user.id)
            # redis_cart = {
            #     商品的sku_id  bytes字节类型: 数量  bytes字节类型
            #     商品的sku_id  bytes字节类型: 数量  bytes字节类型
            #    ...
            # }
            redis_cart_selected = redis_conn.smembers('cart_selected_%s' % user.id)
            # redis_cart_selected = set(勾选的商品sku_id bytes字节类型, ....)

            # 遍历redis_cart, 形成cart_dict
            cart_dict = {}
            for sku_id, count in redis_cart.items():
                cart_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in redis_cart_selected
                }
        else:
            # 如果用户未登录,从cookie中查询
            cookie_cart = request.COOKIES.get('cart')

            if cookie_cart:
                # 表示cookie中有购物车数据
                # 解析
                cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode()))
            else:
                # 表示cookie中没有购物车数据
                cart_dict = {}

        # cart_dict = {
        #     sku_id_1: {
        #         'count': 10
        #         'selected': True
        #     },
        #     sku_id_2: {
        #         'count': 10
        #         'selected': False
        #     },
        # }

        # 查询数据库
        sku_id_list = cart_dict.keys()
        sku_obj_list = SKU.objects.filter(id__in=sku_id_list)

        # 遍历sku_obj_list, 向sku对象中添加count和selected属性
        for sku in sku_obj_list:
            sku.count = cart_dict[sku.id]['count']
            sku.selected = cart_dict[sku.id]['selected']

        # 序列化返回
        serializer = CartSKUSerializer(sku_obj_list, many=True)
        return Response(serializer.data)

    def put(self, request):
        """购物车修改"""
        # 请求参数和返回参数 SKU_id, count, selected
        # 校验
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sku_id = serializer.validated_data['sku_id']
        count = serializer.validated_data['count']
        selected = serializer.validated_data['selected']

        # 判断用户的登录状态
        try:
            user = request.user
        except Exception:
            user = None

        # 保存
        if user and user.is_authenticated:
            # 如果用户已登录,修改redis
            redis_conn = get_redis_connection('cart')
            pl = redis_conn.pipeline()   # 创建redis管道

            # 处理数量 hash
            pl.hset('cart_%s' % user.id, sku_id, count)

            # 处理勾选状态  set
            if selected:
                # 表示勾选(直接添加数据)
                pl.sadd('cart_selected_%s' % user.id, sku_id)
            else:
                # 表示未勾选, 删除
                pl.srem('cart_selected_%s' % user.id, sku_id)

            pl.execute()
            return Response(serializer.data)

        else:
            # 如果未登录,修改cookie
            cookie_cart = request.COOKIES.get('cart')

            if cookie_cart:
                # 表示cookie中有购物车数据
                # 解析
                cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode()))
            else:
                # 表示cookie中没有购物车数据
                cart_dict = {}

            # cart_dict = {
            #     sku_id_1: {
            #         'count': 10
            #         'selected': True
            #     },
            #     sku_id_2: {
            #         'count': 10
            #         'selected': False
            #     },
            # }

            response = Response(serializer.data)

            if sku_id in cart_dict:
                cart_dict[sku_id] = {
                    'count': count,
                    'selected': selected
                }

                cart_cookie = base64.b64encode(pickle.dumps(cart_dict)).decode()

                # 设置cookie
                response.set_cookie('cart', cart_cookie, max_age=constants.CART_COOKIE_EXPIRES)

            return response

    def delete(self, request):
        """删除购物车"""
        # sku_id
        # 校验
        serializer = CartDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sku_id = serializer.validated_data['sku_id']

        # 判断用户的登录状态
        try:
            user = request.user
        except Exception:
            user = None

        # 删除
        if user and user.is_authenticated:
            # 若已登录,删除redis
            redis_conn = get_redis_connection('cart')
            pl = redis_conn.pipeline()

            # 删除 hash
            pl.hdel('cart_%s' % user.id, sku_id)
            # 删除set
            pl.srem('cart_selected_%s' % user.id, sku_id)

            pl.execute()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            # 若未登录,删除cookie
            cookie_cart = request.COOKIES.get('cart')
            if cookie_cart:
                cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode()))
            else:
                cart_dict = {}

            response = Response(status=status.HTTP_204_NO_CONTENT)
            if sku_id in cart_dict:
                del cart_dict[sku_id]

                cart_cookie = base64.b64encode(pickle.dumps(cart_dict)).decode()

                # 设置cookie
                response.set_cookie('cart', cart_cookie, max_age=constants.CART_COOKIE_EXPIRES)

            return response





