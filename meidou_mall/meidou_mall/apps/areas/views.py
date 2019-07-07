from django.shortcuts import render
from rest_framework import serializers
from rest_framework.viewsets import ReadOnlyModelViewSet

from areas.models import Area
from . import serializers


class AreaViewSet(ReadOnlyModelViewSet):

    def get_queryset(self):
        if self.action == 'list':
            return Area.objects.filter(parent=None)
        else:
            return Area.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.AreaSerializer
        else:
            return serializers.SubAreaSerializer
