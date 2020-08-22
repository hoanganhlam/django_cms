from . import views
from rest_framework.routers import DefaultRouter
from django.conf.urls import include, url

router = DefaultRouter()
router.register(r'shipping-addresses', views.ShippingAddressViewSet)
router.register(r'shopping-profiles', views.ShoppingProfileViewSet)
router.register(r'discounts', views.DiscountViewSet)
router.register(r'order-items', views.OrderItemViewSet)
router.register(r'orders', views.OrderViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
