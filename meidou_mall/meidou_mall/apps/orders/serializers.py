import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django_redis import get_redis_connection
from rest_framework import serializers

from goods.models import SKU
from orders.models import OrderInfo, OrderGoods

logger = logging.getLogger('django')


class CartSKUSerializer(serializers.ModelSerializer):
    """
    购物车商品数据序列化器
    """
    count = serializers.IntegerField(label='数量')

    class Meta:
        model = SKU
        fields = ('id', 'name', 'default_image_url', 'price', 'count')


class OrderSettlementSerializer(serializers.Serializer):
    """
    订单结算数据序列化器
    """
    freight = serializers.DecimalField(label='运费', max_digits=10, decimal_places=2)
    skus = CartSKUSerializer(many=True)  # 序列化器嵌套


class SaveOrderSerializer(serializers.ModelSerializer):
    """
    保存订单序列化器
    """
    class Meta:
        model = OrderInfo
        fields = ('address', 'pay_method', 'order_id')
        read_only_fields = ('order_id', )
        extra_kwargs = {
            'address': {
                'write_only': True   # 地址不需要返回, 只需传递到后端
            },
            'pay_method': {
                'required': True   # pay_method有默认值所以默认是不必填的,这里需要指明必填
            }
        }
    def create(self, validated_data):
        """保存订单"""
        address = validated_data['address']
        pay_method = validated_data['pay_method']

        # 获取用户对象  user
        user = self.context['request'].user

        # 查询购物车redis  sku_id  count  selected
        redis_conn = get_redis_connection('cart')
        # hash 商品数量
        redis_cart_dict = redis_conn.hgetall('cart_%s' % user.id)
        # set 勾选商品
        redis_cart_selected = redis_conn.smembers('cart_selected_%s' % user.id)

        # 勾选商品的信息
        cart = {}
        # cart = {
        #     sku_id: count
        # }
        for sku_id in redis_cart_selected:
            cart[int(sku_id)] = int(redis_cart_dict[sku_id])

        if not cart:
            raise serializers.ValidationError('没有需要结算的商品')

        # 创建事务  开启一个事务
        with transaction.atomic():
            try:
                # 创建保存点
                save_id = transaction.savepoint()

                # 保存订单
                # 生成订单编号order_id   20190716175830 + 9位用户id
                order_id = timezone.now().strftime('%Y%m%d%H%M%S') + ('%09d' % user.id)

                # 创建订单基本信息表记录 OrderInfo
                order = OrderInfo.objects.create(
                    order_id = order_id,
                    user = user,
                    address = address,
                    total_count = 0,
                    total_amount = 0,
                    freight = Decimal('10.00'),
                    pay_method = pay_method,
                    # 如果pay_method支付方式等于1(货到付款),status就等于2,待发货
                    status = OrderInfo.ORDER_STATUS_ENUM['UNSEND'] if pay_method==OrderInfo.PAY_METHODS_ENUM['CASH'] else OrderInfo.ORDER_STATUS_ENUM['UNPAID']
                )

                # 查询商品数据库, 获取商品数据(库存)
                sku_id_list = cart.keys()
                # sku_obj_list = SKU.objects.filter(id__in=sku_id_list)

                # 遍历需要结算的商品数据
                for sku_id in sku_id_list:
                    while True:
                        # 查询商品的最新库存信息
                        sku = SKU.objects.get(id=sku_id)

                        # 用户需要购买的数量
                        sku_count = cart[sku.id]
                        origin_stock = sku.stock
                        origin_sales = sku.sales

                        # 判断库存
                        if sku.stock < sku_count:
                            # 回滚到保存点
                            transaction.savepoint_rollback(save_id)
                            raise serializers.ValidationError('商品%s库存不足' % sku.name)

                        # 库存减少 销量增加
                        # sku.stock -= sku_count
                        # sku.sales += sku_count
                        # sku.save()
                        # 解决并发问题
                        new_stock = origin_stock - sku_count
                        new_sales = origin_sales + sku_count

                        # update返回影响的行数
                        result = SKU.objects.filter(id=sku.id, stock=origin_stock).update(stock=new_stock, sales=new_sales)

                        if result == 0:
                            # 表示更新失败, 有人抢了商品
                            # 结束本次while循环,进行下一次while循环
                            continue

                        order.total_count += sku_count
                        order.total_amount += (sku.price * sku_count)

                        # 创建订单商品信息 表记录OrderGoods
                        OrderGoods.objects.create(
                            order = order,
                            sku = sku,
                            count = sku_count,
                            price = sku.price,
                        )
                        #　跳出ｗｈｉｌｅ循环，进行ｆｏｒ循环
                        break

                order.save()   # 更新订单基本信息中的总商品数和总金额
            except serializers.ValidationError:
                raise   # 直接抛出
            except Exception as e:
                logger.error(e)
                transaction.savepoint_rollback(save_id)
                raise  # 捕获完非验证错误,记录完日志,页抛出
            else:
                transaction.savepoint_commit(save_id)

        # 删除购物车中已结算的商品
        pl = redis_conn.pipeline()
        # hash
        pl.hdel('cart_%s' % user.id, *redis_cart_selected)
        # set
        pl.srem('cart_selected_%s' % user.id, *redis_cart_selected)

        pl.execute()

        # 返回OrderInfo对象
        return order