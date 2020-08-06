from django.urls import path, re_path
from apps.authentication.api import views
from rest_framework.routers import DefaultRouter
from django.conf.urls import include, url
from rest_framework_jwt.views import refresh_jwt_token, obtain_jwt_token

router = DefaultRouter()
router.register(r'users', views.UserViewSet)

urlpatterns = [
    path('users/me/', views.UserExt.get_request_user),
    path('obtain-token/', obtain_jwt_token),
    path('refresh-token/', refresh_jwt_token),
    path('rest-auth/', include('rest_auth.urls')),
    path('rest-auth/registration/', include('rest_auth.registration.urls')),
    path('rest-auth/facebook/', views.FacebookLogin.as_view(), name='facebook_login'),
    path('rest-auth/facebook/connect/', views.FacebookConnect.as_view(), name='facebook_connect'),
    path('rest-auth/google/', views.GoogleLogin.as_view(), name='google_login'),
    path('rest-auth/google/connect/', views.GoogleConnect.as_view(), name='google_connect'),
    path('registration/', include('rest_auth.registration.urls')),
    url(r'^', include(router.urls)),
]
