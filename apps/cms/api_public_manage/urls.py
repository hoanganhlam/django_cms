from . import views
from rest_framework.routers import DefaultRouter
from django.conf.urls import include, url

router = DefaultRouter()
router.register(r'taxonomies', views.PubTermViewSet)
router.register(r'posts', views.PostViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^fetch-terms/$', views.fetch_terms),
    url(r'^fetch-terms/(?P<slug>[-\w]+)/$', views.fetch_term),
    url(r'^fetch-terms/(?P<slug>[-\w]+)/fetch-search/$', views.fetch_term_vl),
    url(r'^sync-drive/$', views.sync_drive),
    url(r'^pending-kw/$', views.pending_kw),
    url(r'^taxonomies/(?P<pk>[-\w]+)/sync/$', views.sync_term),
]
