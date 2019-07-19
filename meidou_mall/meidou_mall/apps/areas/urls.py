from django.conf.urls import url
from rest_framework.routers import DefaultRouter

from . import views


urlpatterns = [

]
router = DefaultRouter()  # 创建一个对象
router.register('areas', views.AreaViewSet, base_name='areas')
urlpatterns += router.urls