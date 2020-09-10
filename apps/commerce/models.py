from django.db import models
from base.interface import BaseModel
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField, JSONField
from apps.cms.models import Post, Publication


class Discount(BaseModel):
    name = models.CharField(max_length=50)
    quantity = models.IntegerField(default=0)
    value = models.FloatField(default=0)
    date_start = models.DateTimeField(null=True, blank=True)
    date_end = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    options = JSONField(null=True, blank=True)
    store = models.ForeignKey(Publication, related_name="orders", on_delete=models.CASCADE)


class Address(BaseModel):
    address_components = ArrayField(JSONField(blank=True, null=True), blank=True, null=True)
    geometry = JSONField(blank=True, null=True)
    formatted_address = models.CharField(max_length=250, blank=True, null=True)
    place_id = models.CharField(max_length=250, null=True, blank=True, unique=True)
    types = ArrayField(models.CharField(max_length=250), null=True, blank=True)


class ShoppingProfile(BaseModel):
    user = models.ForeignKey(User, related_name="shopping_profiles", on_delete=models.SET_NULL, null=True, blank=True)
    uid = models.CharField(max_length=100, null=True, blank=True)
    email = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    first_name = models.CharField(max_length=128, null=True, blank=True)
    last_name = models.CharField(max_length=128, null=True, blank=True)


class ShippingAddress(BaseModel):
    phone = models.CharField(max_length=15)
    shopping_profile = models.ForeignKey(ShoppingProfile, related_name="shipping_address", on_delete=models.CASCADE)
    address = models.ForeignKey(
        Address,
        related_name="shipping_address",
        on_delete=models.SET_NULL,
        null=True,
        blank=True)
    formatted_address = models.CharField(max_length=256)
    receiver_name = models.CharField(max_length=128, null=True, blank=True)


class Order(BaseModel):
    shopping_profile = models.ForeignKey(ShoppingProfile, related_name="orders", on_delete=models.CASCADE)
    shipping_address = models.ForeignKey(
        ShippingAddress,
        related_name="orders",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    status = models.CharField(max_length=50, default="SHOPPING")
    note = models.CharField(max_length=512, null=True, blank=True)
    allow_inbox = models.BooleanField(default=True)


class OrderItem(BaseModel):
    shopping_profile = models.ForeignKey(ShoppingProfile, related_name="order_items", on_delete=models.CASCADE)
    order = models.ForeignKey(Order, related_name="order_items", on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Post, related_name="order_items", on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    note = models.CharField(max_length=256, null=True, blank=True)
    meta = JSONField(null=True, blank=True)
    total = models.FloatField(default=0)
    discount = models.ManyToManyField(Discount, related_name="order_items", blank=True)
