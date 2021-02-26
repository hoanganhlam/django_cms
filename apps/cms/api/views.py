from rest_framework import viewsets, permissions
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework import status
from base import pagination
from . import serializers
from apps.cms import models
from django.db.models import Q


class PublicationViewSet(viewsets.ModelViewSet):
    models = models.Publication
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.PublicationSerializer
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['title', 'description']
    lookup_field = 'pk'

    def list(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            queryset = []
        elif not request.user.is_superuser:
            queryset = self.filter_queryset(models.Publication.objects.order_by('-id').filter(user=request.user))
        else:
            queryset = self.filter_queryset(models.Publication.objects.order_by('-id'))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        # instance = self.get_object()
        # self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PostViewSet(viewsets.ModelViewSet):
    models = models.Post
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.PostSerializer
    permission_classes = permissions.IsAdminUser,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['title', 'description']
    lookup_field = 'pk'

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        # instance = self.get_object()
        # self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TermViewSet(viewsets.ModelViewSet):
    models = models.Term
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.TermSerializer
    permission_classes = permissions.IsAdminUser,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['title', 'description']
    lookup_field = 'slug'


class ThemeViewSet(viewsets.ModelViewSet):
    models = models.Theme
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.ThemeSerializer
    permission_classes = permissions.IsAuthenticated,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['title', 'description']
    lookup_field = 'pk'


class PThemeViewSet(viewsets.ModelViewSet):
    models = models.PublicationTheme
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.PThemeSerializer
    permission_classes = permissions.IsAuthenticated,
    pagination_class = pagination.Pagination
    lookup_field = 'pk'

    def list(self, request, *args, **kwargs):
        pub_id = request.GET.get("publication")
        theme_id = request.GET.get("theme")
        q = Q()
        if pub_id:
            q = q & Q(publication__id=pub_id)
        if theme_id:
            q = q & Q(theme__id=theme_id)

        queryset = self.filter_queryset(models.Publication.objects.order_by('-id').filter(q))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
