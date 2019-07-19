import re

from django_redis import get_redis_connection
from rest_framework import serializers
from rest_framework_jwt.settings import api_settings

from celery_tasks.email.task import send_active_email
from goods.models import SKU
from users import constants
from users.models import User, Address


class CreateUserSerializer(serializers.ModelSerializer):
    '''创建用户的序列化器'''
    password2 = serializers.CharField(label='确认密码', write_only=True)
    sms_code = serializers.CharField(label='短信验证码', write_only=True)
    allow = serializers.CharField(label='同意协议', write_only=True)
    token = serializers.CharField(label='JWT token', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'password2', 'sms_code', 'mobile', 'allow', 'token')
        extra_kwargs = {
            'username':{
                'min_length': 5,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许5-20个字符的用户名',
                    'max_length': '仅允许5-20个字符的用户名',
                }
            },
            'password': {
                'write_only': True,
                'min_length': 8,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许8-20个字符的密码',
                    'max_length': '仅允许8-20个字符的密码',
                }
            }
        }

    def validate_mobile(self, value):
        '''验证手机号'''
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式错误')
        return value

    def validate_allow(self, value):
        '''验证用户是否同意协议'''
        if value != 'true':
            raise serializers.ValidationError('请同意用户协议')
        return value

    def validate(self, attrs):
        # 判断两次密码是否一致
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError('两次密码不一致')

        # 判断短信验证码
        redis_conn = get_redis_connection('verify_codes')
        mobile = attrs['mobile']
        real_sms_code = redis_conn.get("sms_%s" % mobile)
        if real_sms_code is None:
            raise serializers.ValidationError("无效的短信验证码")
        if attrs['sms_code'] != real_sms_code.decode():
            raise serializers.ValidationError('短信验证码错误')

        return attrs

    def create(self, validated_data):
        """重写保存方法, 增加密码加密"""

        # 移除数据库模型中不存在的属性
        del validated_data['password2']
        del validated_data['sms_code']
        del validated_data['allow']

        user = User.objects.create(**validated_data)
        # user = super().create(validated_data)  # 这种方法也可以

        user.set_password(validated_data['password'])
        user.save()

        # 签发jwt token
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)

        # 给user增加token属性
        user.token = token

        return user


class UserDetailSerializer(serializers.ModelSerializer):
    """用户详细信息序列化器"""
    class Meta:
        model = User
        fields = ('id', 'username', 'mobile', 'email', 'email_active')


class EmailSerializer(serializers.ModelSerializer):
    """"""
    class Meta:
        model = User
        fields = ('id', 'email')
    # 因为在更新用户邮箱的时候,同时发送邮件,所以重写update方法
    def update(self, instance, validated_data):
        email = validated_data['email']
        instance.email = email
        instance.save()

        # 生成激活链接
        url = instance.generate_verify_email_url()

        # 发送邮件
        send_active_email.delay(email, url)

        return instance


class UserAddressSerializer(serializers.ModelSerializer):
    '''用户地址序列化器'''
    province = serializers.StringRelatedField(read_only=True)
    city = serializers.StringRelatedField(read_only=True)
    district = serializers.StringRelatedField(read_only=True)
    province_id = serializers.IntegerField(label='省ID', required=True)
    city_id = serializers.IntegerField(label='市ID', required=True)
    district_id = serializers.IntegerField(label='区ID', required=True)

    class Meta:
        model = Address
        exclude = ('user', 'is_deleted', 'create_time', 'update_time')

    def validate_mobile(self, value):
        '''验证手机号'''
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式错误')
        return value

    def create(self, validated_data):
        '''保存'''
        # 创建方法重写了为啥呢？因为在保存数据的时候，我们是需要将用户信息保存到数据库中的，
        # 所以需要将user也放到已验证的数据中（因为序列化器中的字段中没有user）
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class AddressTitleSerializer(serializers.ModelSerializer):
    '''地址标题'''
    class Meta:
        model = Address
        fields = ('title',)


class AddUserBrowsingHistorySerializer(serializers.Serializer):
    """
    添加用户浏览历史序列化器
    """
    sku_id = serializers.IntegerField(label='商品SKU编号', min_value=1)

    def validate_sku_id(self, value):
        """
        检验sku_id是否存在
        :param value:
        :return:
        """
        try:
            SKU.objects.get(id=value)
        except SKU.DoesNotExit:
            raise serializers.ValidationError('该商品不存在')
        return value

    def create(self, validated_data):
        """保存"""
        user_id = self.context['request'].user.id
        sku_id = validated_data['sku_id']

        # redis  [1,2,3,4]
        redis_conn = get_redis_connection('history')  # redis 对象
        # print(redis_conn, 1111111111)
        # Redis < ConnectionPool < Connection < host = 127.0.0.1, port = 6379, db = 3 >> > 1111111111
        pl = redis_conn.pipeline()
        # print(pl, 2222222222222)
        # Pipeline < ConnectionPool < Connection < host = 127.0.0.1, port = 6379, db = 3 >> > 2222222222222
        
        # 移除已存在的本商品浏览记录
        pl.lrem('history_%s' % user_id, 0, sku_id)

        # 添加新的浏览记录
        pl.lpush('history_%s' % user_id, sku_id)

        # 只保存最多5条记录
        pl.ltrim('history_%s' % user_id, 0, constants.USER_BROWSING_HISTORY_COUNTS_LIMIT - 1)

        pl.execute()
        # print(validated_data, 33333333333333)
        # {'sku_id': 9} 33333333333333
        return validated_data


class SKUserializer(serializers.ModelSerializer):
    class Meta:
        model = SKU
        fields = ('id', 'name', 'price', 'default_image_url', 'comments')










