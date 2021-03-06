from . import views
from rest_framework.routers import DefaultRouter
from django.conf.urls import include, url
from apps.commerce.api_public import views as commerce

router = DefaultRouter()
router.register(r'shipping-addresses', commerce.ShippingAddressViewSet)
router.register(r'order-items', commerce.OrderItemViewSet)
router.register(r'orders', commerce.OrderViewSet)

urlpatterns = [
    url(r'^pub-(?P<app_id>[-\w]+)/', include(router.urls)),
    url(r'^init/', views.init),
    url(r'^pub/', views.fetch_publication),
    url(r'^graph/', views.graph),
    url(r'^g/', views.graph_v2),
    url(r'^pub-(?P<app_id>[-\w]+)/home/$', views.home),
    url(r'^pub-(?P<app_id>[-\w]+)/shopping-profile/$', commerce.view_shopping_profile),
    url(r'^pub-(?P<app_id>[-\w]+)/taxonomies/$', views.fetch_taxonomies),
    url(r'^pub-(?P<app_id>[-\w]+)/taxonomies/(?P<slug>[-\w]+)/$', views.fetch_taxonomy),
    url(r'^pub-(?P<app_id>[-\w]+)/taxonomies/(?P<slug>[-\w]+)/contrib/$', views.fetch_taxonomy_contribute),
    url(r'^pub-(?P<app_id>[-\w]+)/taxonomies/(?P<slug>[-\w]+)/follow/$', views.follow_term),
    url(r'^pub-(?P<app_id>[-\w]+)/posts/$', views.fetch_posts),
    url(r'^pub-(?P<app_id>[-\w]+)/posts/(?P<slug>[-\w]+)/$', views.fetch_post),
    url(r'^pub-(?P<app_id>[-\w]+)/posts/(?P<slug>[-\w]+)/init/$', views.fetch_post_init),
    url(r'^pub-(?P<app_id>[-\w]+)/posts/(?P<slug>[-\w]+)/comments/$', views.fetch_comments),
    url(r'^pub-(?P<app_id>[-\w]+)/posts/(?P<slug>[-\w]+)/contributions/$', views.fetch_contributions),
    url(r'^pub-(?P<app_id>[-\w]+)/posts/(?P<slug>[-\w]+)/votes/$', views.push_vote),
    url(r'^pub-(?P<app_id>[-\w]+)/posts/(?P<slug>[-\w]+)/follow/$', views.follow),
    url(r'^(?P<app_host>[-\w.]+)/init/', views.public_init),
    url(r'^(?P<app_host>[-\w.]+)/posts/$', views.public_page),
    url(r'^(?P<app_host>[-\w.]+)/posts/(?P<slug>[-\w]+)/$', views.public_post),
]
