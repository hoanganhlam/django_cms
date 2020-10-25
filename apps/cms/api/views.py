from rest_framework import viewsets, permissions
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework import status
from base import pagination
from . import serializers
from apps.cms import models


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
        if request.user.is_authenticated:
            queryset = models.Publication.objects.filter(user=request.user).order_by('-id')
        else:
            queryset = []

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


# class TermTaxonomyViewSet(viewsets.ModelViewSet):
#     models = models.TermTaxonomy
#     queryset = models.objects.select_related("term").order_by('-id')
#     serializer_class = serializers.TermTaxonomySerializer
#     permission_classes = permissions.AllowAny,
#     pagination_class = pagination.Pagination
#     filter_backends = [OrderingFilter, SearchFilter]
#     search_fields = ['term__title', 'term__description']
#     lookup_field = 'pk'
#
#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         term_title = request.data.get("term_title")
#         if term_title is not None:
#             term = models.Term.objects.filter(title=term_title).first()
#             if term is None:
#                 term = models.Term.objects.create(title=term)
#             serializer.is_valid(raise_exception=True)
#             serializer.save(
#                 term=term
#             )
#             headers = self.get_success_headers(serializer.data)
#             return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
#         else:
#             return Response(status=status.HTTP_400_BAD_REQUEST)


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
