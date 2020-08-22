from rest_framework import viewsets, permissions
from rest_framework.filters import OrderingFilter, SearchFilter
from base import pagination
from . import serializers
from apps.commerce import models
from rest_framework import status
from rest_framework.response import Response


class ShoppingProfileViewSet(viewsets.ModelViewSet):
    models = models.ShoppingProfile
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.ShoppingProfileSerializer
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = []
    lookup_field = 'pk'


class ShippingAddressViewSet(viewsets.ModelViewSet):
    models = models.ShippingAddress
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.ShippingAddressSerializer
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = []
    lookup_field = 'pk'


class DiscountViewSet(viewsets.ModelViewSet):
    models = models.Discount
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.DiscountSerializer
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


class OrderViewSet(viewsets.ModelViewSet):
    models = models.Order
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.OrderSerializer
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = []
    lookup_field = 'pk'
