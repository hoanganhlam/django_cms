from rest_framework import viewsets, permissions
from rest_framework.filters import OrderingFilter, SearchFilter
from base import pagination
from . import serializers
from apps.cms import models
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import connection
from utils.other import get_paginator


@api_view(['GET', 'POST'])
def fetch_taxonomies(request):
    if request.method == "GET":
        p = get_paginator(request)
        user_id = request.user.id if request.user.is_authenticated else None
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
                               '{' + request.GET.get('publications') + '}' if request.GET.get('publications') else None,
                           ])
            result = cursor.fetchone()[0]
            if result.get("results") is None:
                result["results"] = []
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)


@api_view(['GET', 'DELETE', 'PUT'])
def fetch_taxonomy(request, slug):
    tax = models.TermTaxonomy.objects.filter(term__slug=slug, taxonomy=request.GET.get("type")).first()
    return Response(serializers.TermTaxonomySerializer(tax).data)


@api_view(['GET', 'POST'])
def fetch_posts(request):
    if request.method == "GET":
        p = get_paginator(request)
        user_id = request.user.id if request.user.is_authenticated else None
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_POSTS(%s, %s, %s, %s, %s, %s, %s, %s)",
                           [
                               p.get("page_size"),
                               p.get("offs3t"),
                               p.get("search"),
                               request.GET.get("order_by"),
                               user_id,
                               request.GET.get("type", None),
                               '{' + request.GET.get('taxonomies') + '}' if request.GET.get('taxonomies') else None,
                               '{' + request.GET.get('publications') + '}' if request.GET.get('publications') else None,
                           ])
            result = cursor.fetchone()[0]
            if result.get("results") is None:
                result["results"] = []
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)


@api_view(['GET', 'DELETE', 'PUT'])
def fetch_post(request, slug):
    if request.method == "GET":
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_POST(%s)", [
                int(slug) if slug.isnumeric() else slug
            ])
            result = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)
