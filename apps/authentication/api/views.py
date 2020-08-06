from rest_framework import views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from apps.authentication.api.serializers import UserSerializer
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from rest_auth.registration.views import SocialLoginView
from rest_framework import viewsets, permissions
from base import pagination
from rest_framework.filters import OrderingFilter
from rest_framework_jwt.settings import api_settings
from rest_framework import status
from django.db import connection
from apps.media.models import Media
from apps.authentication.models import Profile

jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER


class UserViewSet(viewsets.ModelViewSet):
    models = User
    queryset = models.objects.order_by('-id')
    serializer_class = UserSerializer
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter]
    search_fields = ['first_name', 'last_name', 'username']
    lookup_field = 'username'
    lookup_value_regex = '[\w.@+-]+'

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        if instance.id != request.user.id:
            return Response({})
        # PRE
        if instance.profile.options is None:
            instance.profile.options = {}
        if request.data.get("options"):
            instance.profile.options = request.data.get("options")
            instance.profile.save()
        # Start
        if request.data.get("ws"):
            instance.profile.options["ws"] = request.data.get("ws")
        if request.data.get("nick"):
            instance.profile.nick = request.data.get("nick")
        if request.data.get("bio"):
            instance.profile.bio = request.data.get("bio")
        if request.data.get("extra"):
            instance.profile.extra = request.data.get("extra")
        if request.data.get("media"):
            media_instance = Media.objects.get(pk=int(request.data.get("media")))
            instance.profile.media = media_instance
        # END
        instance.profile.save()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def retrieve(self, request, *args, **kwargs):
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_USER_BY_USERNAME(%s, %s)", [
                kwargs["username"],
                request.user.id if request.user.is_authenticated else None
            ])
            out = cursor.fetchone()[0]
        return Response(out)


class UserExt(views.APIView):
    @api_view(['GET'])
    @permission_classes((IsAuthenticated,))
    def get_request_user(request, format=None):
        if not hasattr(request.user, "profile"):
            Profile.objects.create(user=request.user, options={}, extra={})
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_USER_BY_USERNAME(%s, %s)", [
                request.user.username,
                request.user.id if request.user.is_authenticated else None
            ])
            out = cursor.fetchone()[0]
        return Response(out)


class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter


class FacebookConnect(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter


class GoogleConnect(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
