from apps.commerce import models
from rest_framework import serializers
from apps.cms.api.serializers import PostSerializer


class ShoppingProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ShoppingProfile
        fields = '__all__'
        extra_fields = []
        extra_kwargs = {
            'user': {'read_only': True}
        }

    def to_representation(self, instance):
        return super(ShoppingProfileSerializer, self).to_representation(instance)


class ShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ShippingAddress
        fields = '__all__'
        extra_fields = []
        extra_kwargs = {}

    def to_representation(self, instance):
        return super(ShippingAddressSerializer, self).to_representation(instance)


class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Discount
        fields = '__all__'
        extra_fields = []
        extra_kwargs = {}

    def to_representation(self, instance):
        return super(DiscountSerializer, self).to_representation(instance)


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Order
        fields = '__all__'
        extra_fields = []
        extra_kwargs = {}

    def to_representation(self, instance):
        self.fields['shipping_address'] = ShippingAddressSerializer(read_only=True)
        return super(OrderSerializer, self).to_representation(instance)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OrderItem
        fields = '__all__'
        extra_fields = []
        extra_kwargs = {}

    def to_representation(self, instance):
        self.fields['product'] = PostSerializer(read_only=True)
        return super(OrderItemSerializer, self).to_representation(instance)
