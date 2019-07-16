from decimal import Decimal
from django.shortcuts import render
from django_redis import get_redis_connection
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


# Create your views here.
from carts.serializers import CartSKUSerializer
from goods.models import SKU
from orders.serializers import OrderSettlementSerializer


class OrderSettlementView(APIView):
    """
    订单结算
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 获取用户对象 user
        user = request.user

        # 从redis中查询购物车  sku_id   count  selected
        # 1.创建redis连接对象
        redis_conn = get_redis_connection('cart')
        # 2. hash  商品数量
        redis_cart_dict = redis_conn.hgetall('cart_%s' % user.id)
        # 3.set  勾选商品
        redis_cart_selected = redis_conn.smembers('cart_selected_%s' % user.id)

        cart = {}
        for sku_id in redis_cart_selected:
            cart[int(sku_id)] = int(redis_cart_dict[sku_id])

        # 查询数据库
        sku_id_list = cart.keys()
        sku_obj_list = SKU.objects.filter(id__in=sku_id_list)

        for sku in sku_obj_list:
            sku.count = cart[sku.id]

        # 运费
        freight = Decimal('10.00')

        # 序列化返回
        # serializer = CartSKUSerializer(sku_obj_list, many=True)
        # return Response({'freight': freight, 'skus': serializer.data})

        # 利用序列化器嵌套完成返回
        serializer = OrderSettlementSerializer({'freight': freight, 'skus': sku_obj_list})
        return Response(serializer.data)