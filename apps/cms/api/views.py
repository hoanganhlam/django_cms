from rest_framework import viewsets, permissions
from rest_framework.filters import OrderingFilter, SearchFilter
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

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


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
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['title', 'description']
    lookup_field = 'pk'

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TermViewSet(viewsets.ModelViewSet):
    models = models.Term
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.TermSerializer
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['title', 'description']
    lookup_field = 'slug'
