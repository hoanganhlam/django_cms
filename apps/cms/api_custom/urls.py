from . import views
from rest_framework.routers import DefaultRouter
from django.conf.urls import url

router = DefaultRouter()

urlpatterns = [
    url(r'^(?P<host_name>[-\w.]+)/$', views.view_cache),
]
