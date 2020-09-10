from apps.commerce import models
from apps.commerce.api import serializers
from rest_framework.filters import OrderingFilter, SearchFilter
from base import pagination
import uuid
from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import connection
from django.db.models import Q
from utils.other import get_paginator
from rest_framework import status


@api_view(['GET'])
def view_shopping_profile(request, app_id):
    if request.method == "GET":  # Fetch profile
        sp = None
        request_uuid = request.GET.get("uuid", None)
        if request.user.is_authenticated:
            if request_uuid is not None:
                sp = models.ShoppingProfile.objects.filter(uid=request_uuid).first()
                if sp is not None:
                    if sp.user is None:
                        sp.user = request.user
                        sp.save()
            if sp is None:
                sp = models.ShoppingProfile.objects.filter(user=request.user).first()
                if sp is None:
                    sp = models.ShoppingProfile.objects.create(user=request.user, uid=uuid.uuid4())
        else:
            if request_uuid is None:
                sp = models.ShoppingProfile.objects.create(uid=uuid.uuid4())
            else:
                sp = models.ShoppingProfile.objects.filter(uid=request_uuid).first()
                if sp is None:
                    sp = models.ShoppingProfile.objects.create(uid=uuid.uuid4())
        return Response(serializers.ShoppingProfileSerializer(sp).data)
    return Response()


class ShippingAddressViewSet(viewsets.ModelViewSet):
    models = models.ShippingAddress
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.ShippingAddressSerializer
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = []
    lookup_field = 'pk'


class OrderItemViewSet(viewsets.ModelViewSet):
    models = models.OrderItem
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.OrderItemSerializer
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = []
    lookup_field = 'pk'

    def list(self, request, *args, **kwargs):
        p = get_paginator(request)
        user_id = request.user.id if request.user.is_authenticated else None
        with connection.cursor() as cursor:
            cursor.execute("SELECT PUBLIC.FETCH_ORDER_ITEMS(%s, %s, %s, %s, %s, %s)",
                           [
                               p.get("page_size"),
                               p.get("offs3t"),
                               request.GET.get("order_by"),
                               request.GET.get("order", None),
                               None,
                               None
                           ])
            result = cursor.fetchone()[0]
            if result.get("results") is None:
                result["results"] = []
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)


class OrderViewSet(viewsets.ModelViewSet):
    models = models.Order
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.OrderSerializer
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = []
    lookup_field = 'pk'

    def create(self, request, *args, **kwargs):
        items = request.data.get("items")
        if items is None or len(items) == 0:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        instance = models.Order.objects.get(pk=serializer.data.get("id"))
        for item in items:
            item_instance = models.OrderItem.objects.get(pk=item)
            item_instance.order = instance
            item_instance.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
