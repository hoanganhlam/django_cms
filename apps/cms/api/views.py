from rest_framework import viewsets, permissions
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.decorators import api_view
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
        else:
            q = Q()
            if not request.user.is_superuser:
                q = q & Q(user=request.user)
            if request.GET.get("terms"):
                q = q & Q(terms__slug__in=request.GET.get("terms").split(","))
            queryset = self.filter_queryset(models.Publication.objects.filter(q).order_by('-id'))
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

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        active_theme = models.PublicationTheme.objects.filter(publication_id=instance.id, is_active=True).first()
        if active_theme:
            instance.options["theme"] = active_theme.options
            instance.save()
        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)


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

    def list(self, request, *args, **kwargs):
        q = Q()
        if request.GET.get("terms") is not None:
            q = q & Q(id__in=request.GET.get("terms").split(","))
        queryset = self.filter_queryset(models.Term.objects.filter(q).order_by('-id'))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ThemeViewSet(viewsets.ModelViewSet):
    models = models.Theme
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.ThemeSerializer
    permission_classes = permissions.IsAuthenticated,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['title', 'description']
    lookup_field = 'pk'

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PThemeViewSet(viewsets.ModelViewSet):
    models = models.PublicationTheme
    queryset = models.objects.order_by('-id').prefetch_related("theme")
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


@api_view(['GET', 'POST', 'PUT'])
def pub_theme(request, pk):
    active_themes = models.PublicationTheme.objects.filter(publication_id=pk, is_active=True)
    if active_themes.count() >= 1:
        current_active = active_themes.first()
        for theme in active_themes[1:]:
            theme.is_active = False
            theme.save()
    else:
        current_active = None
    # Update theme
    if request.method == "POST" and current_active is not None and current_active.id == request.data.get("id"):
        current_active.options = request.data.get("options")
        current_active.save()
    # Active theme
    if request.method == "PUT" and request.data.get("theme") is not None:
        if current_active is not None and current_active.theme_id == request.data.get("id"):
            pass
        else:
            if current_active is not None:
                current_active.is_active = False
                current_active.save()
            current_active = models.PublicationTheme.objects.create(
                publication_id=pk,
                theme_id=request.data.get("theme"),
                is_active=True
            )
    if request.method in ["POST", "POST"] and current_active is not None:
        publication = models.Publication.objects.get(pk=pk)
        publication.options["theme"] = current_active.options
        publication.save()

    return Response(serializers.PThemeSerializer(current_active).data)
