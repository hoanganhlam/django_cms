from apps.cms import models
from apps.cms.api import serializers
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import connection
from utils.other import get_paginator
from rest_framework import viewsets, permissions
from rest_framework.filters import OrderingFilter, SearchFilter
from base import pagination
import json


class PostViewSet(viewsets.ModelViewSet):
    models = models.Post
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.PostSerializer
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['title', 'description']

    def list(self, request, *args, **kwargs):
        if request.method == "GET":
            p = get_paginator(request)
            user_id = request.user.id if request.user.is_authenticated else None
            with connection.cursor() as cursor:
                meta = json.loads(request.GET.get("meta")) if request.GET.get("meta") else None
                cursor.execute("SELECT FETCH_POSTS(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                               [
                                   p.get("page_size"),
                                   p.get("offs3t"),
                                   p.get("search"),
                                   request.GET.get("order_by"),
                                   user_id,
                                   request.GET.get("post_type", None),
                                   request.GET.get("status", None),
                                   request.GET.get("taxonomies_operator", "OR"),
                                   '{' + request.GET.get('taxonomies') + '}' if request.GET.get('taxonomies') else None,
                                   '{' + request.GET.get("publications") + '}' if request.GET.get("publications",
                                                                                                  None) else None,
                                   request.GET.get("related_operator", "OR"),
                                   '{' + request.GET.get('post_related') + '}' if request.GET.get(
                                       'post_related') else None,
                                   json.dumps(meta) if meta else None,
                                   False
                               ])
                result = cursor.fetchone()[0]
                if result.get("results") is None:
                    result["results"] = []
                cursor.close()
                connection.close()
                return Response(status=status.HTTP_200_OK, data=result)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        with connection.cursor() as cursor:
            slug = kwargs['pk']
            cursor.execute("SELECT FETCH_POST(%s, %s)", [
                int(slug) if slug.isnumeric() else slug,
                request.GET.get("uid") is not None
            ])
            result = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
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
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PubTermViewSet(viewsets.ModelViewSet):
    models = models.PublicationTerm
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.PubTermSerializer
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter]
    lookup_field = 'pk'

    def list(self, request, *args, **kwargs):
        user_id = request.user.id if request.user.is_authenticated else None
        p = get_paginator(request)
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_TERM_TAXONOMIES(%s, %s, %s, %s, %s, %s, %s, %s)",
                           [
                               p.get("page_size"),
                               p.get("offs3t"),
                               p.get("search"),
                               request.GET.get("order_by"),
                               user_id,
                               request.GET.get("taxonomy", None),
                               '{' + request.GET.get('taxonomies') + '}' if request.GET.get('taxonomies') else None,
                               request.GET.get('publication'),
                           ])
            result = cursor.fetchone()[0]
            if result.get("results") is None:
                result["results"] = []
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)

    def create(self, request, *args, **kwargs):
        user_id = request.user.id if request.user.is_authenticated else None
        errors = []
        term = None
        if request.data.get("term"):
            try:
                term = models.Term.objects.get(pk=int(request.data.get("term")))
            except models.Term.DoesNotExist:
                term = None
        else:
            if request.data.get("term_title"):
                term = models.Term.objects.filter(title=request.data.get("term_title")).first()
                if term is None:
                    term = models.Term.objects.create(title=request.data.get("term_title"))

        try:
            pub = models.Publication.objects.get(pk=int(request.data.get("publication")))
        except models.Publication.DoesNotExist:
            pub = None

        if term is None:
            errors.append({"term": "TERM_NONE"})
        if request.data.get("taxonomy") is None:
            errors.append({"taxonomy": "TAXONOMY_NONE"})
        if pub is None:
            errors.append({"publication": "PUBLICATION_NONE"})
        if len(errors) > 0:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=errors)

        tax = models.PublicationTerm.objects.filter(
            publication=pub,
            taxonomy=request.data.get("taxonomy"),
            term=term
        ).first()
        if tax is None:
            tax = models.PublicationTerm.objects.create(
                publication=pub,
                taxonomy=request.data.get("taxonomy"),
                term=term
            )
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_TAXONOMY(%s, %s, %s, %s)", [
                term.slug,
                request.data.get("publication"),
                request.data.get("taxonomy"),
                user_id
            ])
            result = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)

    def retrieve(self, request, *args, **kwargs):
        user_id = request.user.id if request.user.is_authenticated else None
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_TAXONOMY(%s, %s, %s, %s)", [
                kwargs.get("pk"),
                request.GET.get("publication"),
                request.GET.get("taxonomy"),
                user_id
            ])
            result = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
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
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
