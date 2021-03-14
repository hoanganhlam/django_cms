from rest_framework import viewsets, permissions
from rest_framework.filters import OrderingFilter, SearchFilter
from base import pagination
from . import serializers
from apps.media import models
from rest_framework.response import Response
from rest_framework import status


class MediaViewSet(viewsets.ModelViewSet):
    models = models.Media
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.MediaSerializer
    permission_classes = permissions.IsAuthenticatedOrReadOnly,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['title', 'description']
    lookup_field = 'pk'

    def list(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                queryset = self.filter_queryset(models.Media.objects.order_by('-id'))
            else:
                queryset = self.filter_queryset(models.Media.objects.filter(user=request.user).order_by('-id'))
        else:
            queryset = []

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        if not hasattr(serializer.validated_data, "user"):
            serializer.validated_data["user"] = request.user
        self.perform_update(serializer)
        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}
        return Response(serializer.data)

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
