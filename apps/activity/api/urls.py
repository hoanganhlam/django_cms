from . import views
from rest_framework.routers import DefaultRouter
from django.conf.urls import include, url

router = DefaultRouter()
router.register(r'actions', views.ActionViewSet)
router.register(r'comments', views.CommentViewSet)

urlpatterns = [
    url(r'^following', views.list_following),
    url(r'^', include(router.urls)),
    url(r'^is-following', views.is_following),
    url(r'^actions/(?P<pk>[0-9]+)/vote$', views.vote_post),
    url(r'^comments/(?P<pk>[0-9]+)/vote$', views.vote_comment),
    url(r'^follow', views.follow),
    url(r'^check-vote', views.get_vote_object),
]
