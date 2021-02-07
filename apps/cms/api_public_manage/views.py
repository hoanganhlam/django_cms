from apps.cms import models
from apps.cms.api import serializers
from apps.media.models import Media
from apps.media.api.serializers import MediaSerializer
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import connection
from utils.other import get_paginator
from rest_framework import viewsets, permissions
from rest_framework.filters import OrderingFilter, SearchFilter
from base import pagination
from utils.instagram import fetch_by_hash_tag
import json
from apps.cms.tasks import task_sync_drive
from django.template.defaultfilters import slugify
from utils import caching


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
                cursor.execute("SELECT FETCH_POSTS_X(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                               [
                                   p.get("page_size"),
                                   p.get("offs3t"),
                                   p.get("search"),
                                   request.GET.get("order_by"),
                                   user_id,
                                   request.GET.get("post_type", None),
                                   request.GET.get("status", None),
                                   request.GET.get("is_guess_post", None),
                                   request.GET.get("show_cms", None),
                                   request.GET.get("taxonomies_operator", "OR"),
                                   '{' + request.GET.get('taxonomies') + '}' if request.GET.get('taxonomies') else None,
                                   '{' + request.GET.get("publications") + '}' if request.GET.get("publications",
                                                                                                  None) else None,
                                   request.GET.get("related_operator", "OR"),
                                   '{' + request.GET.get('post_related') + '}' if request.GET.get(
                                       'post_related') else None,
                                   request.GET.get("related", None),
                                   json.dumps(meta) if meta else None
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
            cursor.execute("SELECT FETCH_POST(%s, %s, %s, %s, %s)", [
                int(slug) if slug.isnumeric() else slug,
                request.GET.get("uid") is not None,
                request.GET.get("is_guess_post"),
                request.GET.get("show_cms"),
                request.user.id
            ])
            result = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=False)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if request.data.get("post_related"):
            related = models.Post.objects.filter(id__in=request.data.get("post_related"))
            old_related = instance.post_related.all()
            for r in related:
                if r not in old_related:
                    instance.post_related.add(r)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}
        return Response(
            status=status.HTTP_200_OK,
            data=caching.make_post(True, instance.primary_publication.host, str(instance.id), {"master": True}))

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.db_status = -1
        instance.save()
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
                term, is_created = models.Term.objects.get_or_create(
                    slug=slugify(request.data.get("term_title")),
                    defaults={
                        "title": request.data.get("term_title")
                    }
                )
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
            term=term,
            db_status=1
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

        return Response(
            status=status.HTTP_200_OK,
            data=caching.make_term(True, str(instance.id), False))


@api_view(['GET'])
def fetch_ig_post(request):
    if request.method == "GET":
        out = fetch_by_hash_tag(request.GET.get("search"), request.GET.get("next", None))
        return Response(out)


@api_view(['POST'])
def import_ig_post(request):
    if request.method == "POST":
        items = request.data.get("items", [])
        pub = models.Publication.objects.get(pk=request.data.get("pub"))
        related = models.Post.objects.filter(id__in=request.data.get("related", []))
        for item in items:
            instance = models.Post.objects.filter(meta__ig_id=item.get("ig_id")).first()
            if instance is None and len(item.get("images", [])) > 0:
                medias = []
                for img in item.get("images", []):
                    media = Media.objects.save_url(img)
                    medias.append(media.id)
                    print(MediaSerializer(media).data.get("id"))
                meta = {
                    "ig_id": item.get("ig_id"),
                    "credit": item.get("user").get("username"),
                    "medias": medias
                }
                instance = models.Post.objects.create(
                    title="Post by " + item.get("user").get("full_name") if item.get("user").get(
                        "full_name") else item.get("user").get("username"),
                    description=item.get("caption")[:300] if item.get("caption") else None,
                    meta=meta,
                    primary_publication=pub,
                    user=request.user,
                    post_type=request.data.get("post_type", "post"),
                    show_cms=True,
                    status="POSTED"
                )
                for r in related:
                    instance.post_related.add(r)
                    instance.publications.add(pub)
        return Response({})


@api_view(['GET', 'POST'])
def fetch_terms(request):
    if request.method == "GET":
        p = get_paginator(request)
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_TERMS_WITH_SEARCH(%s, %s, %s, %s, %s, %s)",
                           [
                               p.get("page_size"),
                               p.get("offs3t"),
                               p.get("search"),
                               request.GET.get("order_by"),
                               request.GET.get("taxonomy", None),
                               request.GET.get("pub", None)
                           ])
            result = cursor.fetchone()[0]
            if result.get("results") is None:
                result["results"] = []
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)
    if request.method == "POST":
        term, created = models.Term.objects.get_or_create(title=request.data.get("title"), defaults={
            "options": {"need_fetch": True}
        })
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_TERM_WITH_TAX(%s, %s)", [
                term.slug,
                request.GET.get("pub")
            ])
            result = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)


@api_view(['GET'])
def fetch_term(request, slug):
    if request.method == "GET":
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_TERM_WITH_TAX(%s, %s)", [
                slug,
                request.GET.get("pub")
            ])
            result = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)
    return Response()


@api_view(['GET'])
def fetch_term_vl(request, slug):
    if request.method == "GET":
        kw = models.SearchKeyword.objects.filter(slug=slug).first()
        if kw is None:
            term = models.Term.objects.get(slug=slug)
            kw = models.SearchKeyword.objects.create(title=term.title, fetch_status="queue")
        else:
            kw.fetch_status = "queue"
            kw.save()
        return Response({"id": kw.id, "fetch_status": "queue"})
    return Response()


@api_view(['POST', "GET"])
def sync_drive(request):
    if request.method == "GET":
        file_name = request.GET.get("name")
        kw = models.SearchKeyword.objects.filter(title=request.GET.get("kw")).first()
        if kw:
            kw.fetch_status = "fetching"
            kw.save()
        task_sync_drive.apply_async(
            args=["file_name"],
            kwargs={"file_name": file_name},
            countdown=1
        )
        return Response()


@api_view(["GET"])
def pending_kw(request):
    kws = models.SearchKeyword.objects.filter(fetch_status="queue", searches__isnull=True)
    return Response(list(map(lambda x: x.title, kws)))

# Create term => save with flag* => app_helper fetch and search => call to sync_drive => save()
