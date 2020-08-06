#!/usr/bin/python
# -*- coding: utf8 -*-


from abc import ABCMeta, abstractmethod
from rest_framework import generics, filters, mixins, authentication, permissions, viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.views import APIView
from rest_framework.settings import api_settings
from rest_framework.response import Response

class DeleteListMixin(object):
    def delete_list(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.delete_list()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BaseUpdateModelMixin(mixins.UpdateModelMixin):
    def update(self, request, *args, **kwargs):
        # default partial update
        partial = kwargs.pop('partial', True)
        return super(BaseUpdateModelMixin, self).update(request, partial=partial, *args, **kwargs)


class CoreView(mixins.CreateModelMixin,
               mixins.RetrieveModelMixin,
               mixins.UpdateModelMixin,
               mixins.DestroyModelMixin,
               mixins.ListModelMixin,
               generics.GenericAPIView):
    pass


class RawPostMixin(object):
    def post(self, request, *args, **kwargs):
        pass

def BaseView(*kwargs):
    _actinMixinList = []

    if 'create' in kwargs:
        _actinMixinList.append(mixins.CreateModelMixin)

    if 'list' in kwargs:
        _actinMixinList.append(mixins.ListModelMixin)

    if 'show' in kwargs:
        _actinMixinList.append(mixins.RetrieveModelMixin)

    if 'edit' in kwargs:
        _actinMixinList.append(BaseUpdateModelMixin)

    if 'delete' in kwargs:
        _actinMixinList.append(mixins.DestroyModelMixin)

    if 'delete_list' in kwargs:
        _actinMixinList.append(DeleteListMixin)

    if 'post' in kwargs:
        _actinMixinList.append(RawPostMixin)

    if len(_actinMixinList) <= 0:
        _actinMixinList = [
            mixins.CreateModelMixin,
            mixins.RetrieveModelMixin,
            mixins.UpdateModelMixin,
            mixins.DestroyModelMixin,
            mixins.ListModelMixin,
            DeleteListMixin,
            # RawPostMixin,
        ]

    _actinMixinList.append(generics.GenericAPIView)

    return _actinMixinList


class BaseModelViewSet(viewsets.ModelViewSet):
    pass


class ReadOnlyBaseModelViewSet(viewsets.ReadOnlyModelViewSet):
    pass


class DefaultsMixin(object):
    '''
        phần mixer cấu hình chung cho các viewset
    '''

    authentication_classes = (
        JSONWebTokenAuthentication,
    )
    permission_classes = (
        permissions.IsAuthenticated,
    )

    paginate_by = 25
    paginate_by_param = 'page_size'
    max_paginate_by = 100
    filter_backends = (
        # filters.BaseFilterBackend,
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    # ordering_fields = ('-id', '-created',)

    ordering_fields = '__all__'
    ordering = ('-id',)


class UpdateHookMixin(object):

    def perform_create(self, serializer):
        super().perform_create(serializer)
        # self._send_hook_request(serializer.instance, 'POST')

    def perform_update(self, serializer):
        super().perform_update(serializer)
        # self._send_hook_request(serializer.instance, 'PUT')

    def perform_destroy(self, instance):
        # self._send_hook_request(instance, 'DELETE')
        super().perform_destroy(instance)


class BaseViewMixin(DefaultsMixin, UpdateHookMixin):
    pass


class BaseAPIView(APIView):
    pass


class MessageResponse(object):
    def __init__(self, **kwargs):
        self.success = True
        self.message = ''
        self.data = None

        for key, value in kwargs.items():
            setattr(self, key, value)

    def setAttr(self, key, val):
        self.__setattr__(key, val)

    def getAttr(self):
        return self.__dict__

    # def __str__(self):
    #     return  self.__dict__()

