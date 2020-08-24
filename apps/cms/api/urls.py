from . import views
from rest_framework.routers import DefaultRouter
from django.conf.urls import include, url

router = DefaultRouter()
router.register(r'posts', views.PostViewSet)
router.register(r'publications', views.PublicationViewSet)
router.register(r'terms', views.TermViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
