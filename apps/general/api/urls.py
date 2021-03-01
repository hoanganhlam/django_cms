from . import views
from rest_framework.routers import DefaultRouter
from django.conf.urls import include, url

router = DefaultRouter()

urlpatterns = [
    url(r'^set-pub', views.set_pub),
    url(r'^set-term', views.set_term),
    url(r'^fetch', views.fetch_url),
]
