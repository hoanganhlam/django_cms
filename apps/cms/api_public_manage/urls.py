from . import views
from rest_framework.routers import DefaultRouter
from django.conf.urls import include, url

router = DefaultRouter()
# router.register(r'posts', views.PostViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^taxonomies/$', views.fetch_taxonomies),
    url(r'^taxonomies/(?P<slug>[-\w]+)/$', views.fetch_taxonomy),
    url(r'^posts/$', views.fetch_posts),
    url(r'^posts/(?P<slug>[-\w]+)/$', views.fetch_post),
]
