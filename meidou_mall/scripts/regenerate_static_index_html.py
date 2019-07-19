#!/usr/bin/env python

"""
功能：手动生成index html文件
使用方法:
    ./regenerate_static_index_html.py
"""
import sys
sys.path.insert(0, '../')
sys.path.insert(0, '../meidou_mall/apps')

import os
if not os.getenv('DJANGO_SETTINGS_MODULE'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'meidou_mall.settings.dev'

 # 让django进行初始化设置
import django
django.setup()


from contents.crons import generate_static_index_html


if __name__ == '__main__':
    generate_static_index_html()