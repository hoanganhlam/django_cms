from . import views
from rest_framework.routers import DefaultRouter
from django.conf.urls import include, url

router = DefaultRouter()
router.register(r'posts', views.PostViewSet)
router.register(r'publications', views.PublicationViewSet)
router.register(r'terms', views.TermViewSet)
router.register(r'themes', views.ThemeViewSet)
router.register(r'p-themes', views.PThemeViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^publications/(?P<app_id>[-\w]+)/theme/$', views.pub_theme),
]
