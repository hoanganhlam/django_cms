from . import views
from rest_framework.routers import DefaultRouter
from django.conf.urls import include, url

router = DefaultRouter()
router.register(r'taxonomies', views.PubTermViewSet)
router.register(r'posts', views.PostViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^fetch-ig$', views.fetch_ig_post),
    url(r'^import-ig$', views.import_ig_post),
]
