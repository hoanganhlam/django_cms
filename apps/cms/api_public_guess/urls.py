from . import views
from rest_framework.routers import DefaultRouter
from django.conf.urls import include, url

router = DefaultRouter()

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^pub-(?P<app_id>[-\w]+)/taxonomies/$', views.fetch_taxonomies),
    url(r'^pub-(?P<app_id>[-\w]+)/taxonomies/(?P<slug>[-\w]+)/$', views.fetch_taxonomy),
    url(r'^pub-(?P<app_id>[-\w]+)/posts/$', views.fetch_posts),
    url(r'^pub-(?P<app_id>[-\w]+)/posts/(?P<slug>[-\w]+)/$', views.fetch_post),
    url(r'^pub-(?P<app_id>[-\w]+)/posts/(?P<slug>[-\w]+)/comments$', views.fetch_comments),
    url(r'^pub-(?P<app_id>[-\w]+)/posts/(?P<slug>[-\w]+)/votes$', views.push_vote),
]
