from django_redis import get_redis_connection
from rest_framework import serializers
from rest_framework_jwt.settings import api_settings

from oauth.models import OAuthQQUser
from oauth.utils import OAuthQQ
from users.models import User


class OAuthQQUserSerializer(serializers.ModelSerializer):
    """"""
    sms_code = serializers.CharField(label='短信验证码', write_only=True)
    access_token = serializers.CharField(label='操作凭证', write_only=True)
    token = serializers.CharField(read_only=True)
    mobile = serializers.RegexField(label='手机号', regex=r'^1[3-9]\d{9}$')

    class Meta:
        model = User
        fields = ('mobile', 'password', 'sms_code', 'access_token', 'id', 'username', 'token')
        extra_kwargs = {
            'username':{
                'read_only': True
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

    def validate(self, attrs):
        # 校验access_token
        access_token = attrs['access_token']

        openid = OAuthQQ.check_bind_user_access_token(access_token)
        if not openid:
            raise serializers.ValidationError('无效的access_token')
        attrs['openid'] = openid

        # 校验短信验证码
        mobile = attrs['mobile']
        sms_code = attrs['sms_code']
        # print(sms_code,111111111111111111)
        # 276842 111111111111111111
        redis_conn = get_redis_connection('verify_codes')
        real_sms_code = redis_conn.get('sms_%s' % mobile).decode()

        if real_sms_code != sms_code:
            raise serializers.ValidationError('短信验证码错误')

        # 如果用户存在,检查用户密码
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            pass
        else:
            password = attrs['password']
            if not user.check_password(password):
                raise serializers.ValidationError('密码错误')

            attrs['user'] = user

        return attrs

    def create(self, validated_data):
        openid = validated_data['openid']
        user = validated_data.get('user')
        mobile = validated_data['mobile']
        password = validated_data['password']

        # 判断用户是否存在
        if not user:
            user = User.objects.create_user(username=mobile, mobile=mobile, password=password)
        OAuthQQUser.objects.create(user=user, openid=openid)

        # 签发JWT token
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)

        user.token = token
        self.context['view'].user = user
        return user

