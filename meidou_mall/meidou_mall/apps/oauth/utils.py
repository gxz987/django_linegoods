import re
from urllib.parse import urlencode, parse_qs
from urllib.request import urlopen
from itsdangerous import TimedJSONWebSignatureSerializer as TJWSSerializer, BadData
from django.conf import settings
import json
import logging

from oauth import constants
from oauth.exceptions import OAuthQQAPIError

logger = logging.getLogger('django')


class OAuthQQ(object):
    """QQ认证辅助工具类"""
    def __init__(self, client_id=None, client_secret=None, redirect_uri=None, state=None):
        self.client_id = client_id if client_secret else settings.QQ_CLIENT_ID
        self.redirect_uri = redirect_uri if redirect_uri else settings.QQ_REDIRECT_URI
        self.state = state or settings.QQ_STATE  # 用于保存登录成功后的跳转页面路径
        self.client_secret = client_secret if client_secret else settings.QQ_CLIENT_SECRET

    def get_login_url(self):
        """
        获取qq登录的网址
        :return: url网址
        """
        url = 'https://graph.qq.com/oauth2.0/authorize?'
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'state': self.state,
        }

        url += urlencode(params)
        return url

    def get_access_token(self, code):
        """获取access_token"""
        url = 'https://graph.qq.com/oauth2.0/token?'
        params = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri,
        }
        url += urlencode(params)

        try:
            # 发送请求
            resp = urlopen(url)
            # 读取响应体的数据
            resp_data = resp.read()  # bytes
            resp_data = resp_data.decode()  # str

            # access_token=FE04************************CCE2&expires_in=7776000&refresh_token=88E4************************BE14

            # print(resp_data)
            # 解析access_token
            resp_dict = parse_qs(resp_data)
        except Exception as e:
            logger.error('获取access_token异常:%s' % e)
            raise OAuthQQAPIError
        else:
            access_token = resp_dict.get('access_token')
            # print("access_token: %s" % access_token)
            # access_token: ['BB8992BE8D6C316F98817EC254DD88C0']
            return access_token[0]

    def get_openid(self, access_token):
        url = 'https://graph.qq.com/oauth2.0/me?access_token=' + access_token

        try:
            # 发送请求
            resp = urlopen(url)
            # 读取响应体的数据
            resp_data = resp.read().decode()
            # print(resp_data, 11111111111111)
            # callback({"client_id": "101474184", "openid": "EA06C7AAB5468836A67B1229A7B6A582"});
            # 11111111111111

            # callback( {"client_id":"YOUR_APPID","openid":"YOUR_OPENID"} )\n;

            # 解析一:通过切片
            resp_data = resp_data[10:-4]
            # print(resp_data, 2222222222222222222)
            # '{"client_id": "101474184", "openid": "EA06C7AAB5468836A67B1229A7B6A582"}' 2222222222222222222
            # 解析二:通过正则
            # resp_data = re.findall(r'[^{].*}$', resp_data)
            resp_dict = json.loads(resp_data)
        except Exception as e:
            logger.error('获取openid异常: %s' % e)
            raise OAuthQQAPIError
        else:
            openid = resp_dict.get('openid')

            return openid

    def generate_bind_user_access_token(self, openid):
        serializer = TJWSSerializer(settings.SECRET_KEY, constants.BIND_USER_ACCESS_TOKEN_EXPIRES)
        token = serializer.dumps({'openid': openid})
        return token.decode()

    @staticmethod
    def check_bind_user_access_token(access_token):
        """在access_token中提取openid"""
        serializer = TJWSSerializer(settings.SECRET_KEY, constants.BIND_USER_ACCESS_TOKEN_EXPIRES)
        try:
            data = serializer.loads(access_token)
        except BadData:
            return None
        else:
            return data['openid']
