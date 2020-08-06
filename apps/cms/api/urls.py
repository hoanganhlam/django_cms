from . import views
from rest_framework.routers import DefaultRouter
from django.conf.urls import include, url

router = DefaultRouter()
router.register(r'posts', views.PostViewSet)
router.register(r'term-taxonomies', views.TermTaxonomyViewSet)
router.register(r'publications', views.PublicationViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
