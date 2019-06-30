import logging

from rest_framework import status
from rest_framework.response import Response

from celery_tasks.main import celery_app
from meidou_mall.utils.yuntongxun.sms import CCP
from verifications import constants


logger = logging.getLogger('django')

@celery_app.task(name='send_sms_code')
def send_sms_code(mobile, sms_code, expires, temp_id):
    '''发送短信验证码'''
    try:
        ccp = CCP()
        expires = constants.SMS_CODE_REDIS_EXPIRES // 60
        result = ccp.send_template_sms(mobile, [sms_code, expires], constants.SMS_CODE_TEMP_ID)
    except Exception as e:
        logger.error('发送短信验证码[异常][ mobile: %s, message: %s]' % (mobile, e))
    else:
        if result == 0:
            logger.info('发送短信验证码[正常][ mobile: %s]' % mobile)
        else:
            logger.warning('发送短信验证码[失败][ mobile: %s ]' % mobile)
