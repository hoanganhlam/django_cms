from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Q
from django.core.cache import cache
from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from apps.activity import verbs, action
from apps.cms.models import Post, Publication, Term, PublicationTerm
from apps.cms.api import serializers
from apps.authentication.api.serializers import UserSerializer
from apps.cms import models
from apps.activity import actions
from apps.activity.models import Comment, Action
from apps.activity.api.serializers import CommentSerializer
from utils.other import get_paginator, clone_dict
from utils.query import query_post, query_posts, query_publication, query_user
from utils import caching, filter_query, caching_v2
from django.contrib.contenttypes.models import ContentType

CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)


def get_action_id(app_id, slug, flag):
    if flag:
        q = Q(uid=int(slug))
    else:
        if slug.isnumeric():
            q = Q(id=int(slug))
        else:
            q = Q(slug=slug)
    post = models.Post.objects.filter(q).first()
    if post is not None:
        if post.options is None:
            post.options = {}
        old_action = Action.objects.filter(id=post.options.get("action_post", 0)).first()
        if old_action is None and post.status == "POSTED":
            new_action = action.send(
                post.user,
                verb=verbs.POST_CREATED,
                action_object=post,
                target=post.primary_publication if post.primary_publication is not None else None
            )
            old_action = new_action[0][1]
            post.options['action_post'] = old_action.id
            post.save()
        return old_action.id
    return None


def is_equal(a, b):
    if type(a) == list:
        return str(a) == str(b)
    elif type(a) == object:
        return str(a) == str(b)
    else:
        return a == b


# ==========================================================================
@api_view(['GET', 'POST'])
def init(request):
    return Response(status=status.HTTP_200_OK, data={
        "p": caching_v2.maker_pub(
            request.GET.get("host"),
            request.data if request.method == "POST" else {},
            request.GET.get("force")
        ),
        "u": caching_v2.make_user(
            request.GET.get("host"),
            {"value": request.user.username},
            request.GET.get("force")) if request.user.is_authenticated else None
    })


@api_view(['GET'])
def home(request, app_id):
    if request.method == "GET":
        key = "pub_home_" + str(app_id)
        force = request.GET.get("force", False)
        if key in cache and force is False:
            data = cache.get(key)
        else:
            pub = None
            if app_id != "0":
                if app_id.isdigit():
                    pub = Publication.objects.get(pk=app_id)
                else:
                    pub = Publication.objects.get(slug=app_id)
            terms = Term.objects.filter()[:5]
            posts = Post.objects.filter(post_type="article")[:11]
            users = User.objects.filter()[:16]
            publications = Publication.objects.filter()[:12]
            data = {
                "terms": serializers.TermSerializer(terms, many=True).data,
                "posts": serializers.PostSerializer(posts, many=True).data,
                "users": UserSerializer(users, many=True).data,
                "publications": serializers.PublicationSerializer(publications, many=True).data,
                "pub": serializers.PublicationSerializer(pub).data
            }
            cache.set(key, data, timeout=CACHE_TTL)
        return Response(data)


@api_view(['GET'])
def fetch_publication(request):
    if request.method == "GET":
        return Response(status=status.HTTP_200_OK, data=query_publication(request.GET.get("host")))


@api_view(['GET', 'POST'])
def fetch_taxonomies(request, app_id):
    pub = Publication.objects.get(pk=app_id)
    if request.method == "GET":
        search = request.GET.get('search')
        page_size = 10 if request.GET.get('page_size') is None else int(request.GET.get('page_size'))
        page = 1 if request.GET.get('page') is None else int(request.GET.get('page'))
        auth_id = request.user.id if request.user.is_authenticated else None
        user_id = request.get("user")
        taxonomy = request.get("taxonomy")
        meta = request.get("meta")
        related = request.GET.get('related_terms').split(",") if request.GET.get('related_terms') else None
        q = Q(show_cms=True, publication_id=app_id)
        if taxonomy:
            q = q & Q(taxonomy=taxonomy)
        if related:
            q = q & Q(related__id__in=related)
        if search:
            q = q & Q(term__title__icontains=search) | Q(term__description__icontains=search)
        queryset = models.PublicationTerm.objects.order_by("-id").values_list("id", flat=True).filter(q)
        paginator = Paginator(queryset, page_size)
        terms = list(paginator.page(page).object_list)
        results = []
        for item in terms:
            results.append(
                clone_dict(
                    caching_v2.make_term(pub.host, {"instance": item}, False),
                    ["id", "term", "taxonomy"],
                    None
                )
            )
        return Response(status=status.HTTP_200_OK, data={
            "results": results,
            "count": queryset.count()
        })


@api_view(['GET', 'POST'])
def fetch_posts(request, app_id):
    pub = Publication.objects.get(pk=app_id)
    if request.method == "GET":
        search = request.GET.get('search')
        page_size = 10 if request.GET.get('page_size') is None else int(request.GET.get('page_size'))
        page = 1 if request.GET.get('page') is None else int(request.GET.get('page'))
        auth_id = request.user.id if request.user.is_authenticated else None
        user_id = request.GET.get("user")
        post_type = request.GET.get("post_type")
        terms = request.GET.get("terms").split(",") if request.GET.get("terms") else []
        related_posts = request.GET.get("related_posts").split(",") if request.GET.get("related_posts") else []
        meta = request.GET.get("meta")
        q = Q(show_cms=True, primary_publication_id=app_id)
        if user_id:
            q = q & Q(user_id=user_id)
        if post_type:
            q = q & Q(post_type=post_type)
        if terms:
            q = q & Q(terms__id__in=terms)
        if search:
            q = q & (Q(title__icontains=search) | Q(description__icontains=search))
        if related_posts:
            q = q & Q(post_related__id__in=related_posts)
        queryset = models.Post.objects.order_by("-id").values_list("id", flat=True).filter(q)
        paginator = Paginator(queryset, page_size)
        posts = list(paginator.page(page).object_list)
        results = []
        for post in posts:
            results.append(
                clone_dict(
                    caching_v2.make_post(pub.host, {"instance": post}, False),
                    ["title", "id", "post_type", "description", "media", "slug"],
                    None
                )
            )
        return Response(status=status.HTTP_200_OK, data={
            "results": results,
            "count": queryset.count()
        })
    if request.method == "POST":
        if pub.options.get("allow_guess_post", False):
            meta = request.data.get("meta", {})
            post = Post.objects.create(
                primary_publication=pub,
                status="POSTED",
                show_cms=pub.options.get("auto_guess_public", False) or (request.user.is_authenticated and request.user.is_staff),
                post_type=request.data.get("post_type", "article"),
                title=request.data.get("title", "Untitled"),
                description=request.data.get("description"),
                content=request.data.get("content"),
                user=request.user if request.user.is_authenticated else None,
                meta=meta,
                is_guess_post=True
            )
            if request.data.get("post_related_add", None) is not None:
                for p in request.data.get("post_related_add", None):
                    pr = Post.objects.get(pk=p)
                    post.post_related.add(pr)
                    if pub.options.get("auto_guess_public", False):
                        for order in ["p", "n"]:
                            key_path_post = "term_{}_{}_{}".format(p.id, post.post_type, order)
                            ids = p.make_posts(post.post_type, order)
                            cache.set(key_path_post, list(ids), timeout=CACHE_TTL)
            if request.data.get("terms_add", None) is not None:
                prs = PublicationTerm.objects.filter(id__in=request.data.get("terms_add", []))
                for p in prs:
                    post.terms.add(p)
                    if pub.options.get("auto_guess_public", False):
                        for order in ["p", "n"]:
                            key_path_post = "term_{}_{}_{}".format(p.id, post.post_type, order)
                            ids = p.make_posts(post.post_type, order)
                            cache.set(key_path_post, list(ids), timeout=CACHE_TTL)
            if request.user.is_authenticated:
                actions.follow(request.user, post)
            if pub.options.get("auto_guess_public", False):
                for order in ["p", "n"]:
                    key_path = "{}_{}_{}".format(post.primary_publication.host, post.post_type, order)
                ids = post.primary_publication.make_posts(post.post_type, order)
                cache.set(key_path, ids, timeout=CACHE_TTL * 12)
            return Response(
                status=status.HTTP_200_OK,
                data=caching.make_post(True, None, str(post.id), {"master": True})
            )
        return Response(status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET', 'DELETE', 'PUT'])
def fetch_taxonomy(request, app_id, slug):
    user_id = request.user.id if request.user.is_authenticated else None
    if request.method == "GET":
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_TAXONOMY(%s, %s, %s, %s)", [
                slug,
                app_id,
                request.GET.get("taxonomy"),
                user_id
            ])
            result = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)
    if request.method == "PUT":
        instance = PublicationTerm.objects.get(id=slug, publication_id=app_id)
        is_authenticated = request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff)
        ct = ContentType.objects.get(app_label='cms', model='publicationterm')
        for k in request.data.keys():
            if k in ["meta", "options"]:
                for km in request.data.get(k):
                    if not is_equal(request.data.get(k).get(km), getattr(instance, k).get(km)):
                        val = request.data.get(k).get(km)
                        models.Contribute.objects.create(
                            user=request.user if request.user.is_authenticated else None,
                            target_content_type=ct,
                            target_object_id=instance.id,
                            field="{}__{}".format(k, km),
                            value=val,
                            type=type(val).__name__,
                            status="approved" if is_authenticated else "pending"
                        )
            else:
                if not is_equal(request.data.get(k), getattr(instance, k)):
                    models.Contribute.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        target_content_type=ct,
                        target_object_id=instance.id,
                        field=k,
                        value=request.data.get(k),
                        type=type(request.data.get(k)),
                        status="approved" if is_authenticated else "pending"
                    )
        if is_authenticated:
            for k in request.data.keys():
                if k in ["meta", "options"]:
                    if getattr(instance, k) is None:
                        setattr(instance, k, {})
                    for key in request.data.get(k).keys():
                        if k == "meta":
                            instance.meta[key] = request.data.get("meta")[key]
                        else:
                            instance.options[key] = request.data.get("options")[key]
                else:
                    setattr(instance, k, request.data.get(k))
            instance.save()
            flag = True
        else:
            flag = False
        return Response(
            status=status.HTTP_200_OK,
            data=caching_v2.make_term(instance.publication.host, {"instance": instance.id, "is_page": True}, flag)
        )
    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED, )


@api_view(['GET', 'DELETE', 'PUT'])
def fetch_post(request, app_id, slug):
    publication = Publication.objects.get(pk=app_id)
    if request.method == "PUT":
        instance = Post.objects.get(pk=slug)
        is_authenticated = request.user.is_authenticated and (
                request.user.is_superuser or request.user.is_staff or request.user is instance.user)
        if request.user.is_authenticated and request.user not in instance.collaborators.all():
            instance.collaborators.add(request.user)
        if is_authenticated:
            if request.data.get("title"):
                instance.title = request.data.get("title")
            if request.data.get("show_cms"):
                instance.show_cms = request.data.get("show_cms")
            if request.data.get("description") or request.data.get("description") == "":
                instance.description = request.data.get("description")
            if request.data.get("content") is not None:
                instance.content = request.data.get("content")
            if request.data.get("meta"):
                if instance.meta is None:
                    instance.meta = {}
                for key in request.data.get("meta").keys():
                    instance.meta[key] = request.data.get("meta")[key]
            if request.data.get("post_related_removal"):
                for p in request.data.get("post_related_removal"):
                    pr = Post.objects.get(pk=p)
                    instance.post_related.remove(pr)
            if request.data.get("post_related_add"):
                for p in request.data.get("post_related_add"):
                    pr = Post.objects.get(pk=p)
                    instance.post_related.add(pr)
            if request.data.get("terms_removal"):
                for p in request.data.get("terms_removal"):
                    pr = PublicationTerm.objects.get(pk=p)
                    instance.terms.remove(pr)
                    for order in ["p", "n"]:
                        key_path_post = "term_{}_{}_{}".format(pr.id, instance.post_type, order)
                        ids = pr.make_posts(instance.post_type, order)
                        cache.set(key_path_post, list(ids), timeout=CACHE_TTL * 12)
            if request.data.get("terms_add"):
                for p in request.data.get("terms_add"):
                    pr = PublicationTerm.objects.get(pk=p)
                    instance.terms.add(pr)
                    for order in ["p", "n"]:
                        key_path_post = "term_{}_{}_{}".format(pr.id, instance.post_type, order)
                        ids = pr.make_posts(instance.post_type, order)
                        cache.set(key_path_post, list(ids), timeout=CACHE_TTL * 12)
            for order in ["p", "n"]:
                key_path = "{}_{}_{}".format(instance.primary_publication.host, instance.post_type, order)
                ids = instance.primary_publication.make_posts(instance.post_type, order)
                cache.set(key_path, ids, timeout=CACHE_TTL * 12)
            instance.save()
            flag = True
        else:
            flag = False
        ct = ContentType.objects.get(app_label='cms', model='post')
        for k in request.data.keys():
            val = request.data.get(k)
            field = k
            if k in ["post_related_add", "post_related_removal"]:
                typ3 = "post"
            elif k in ["terms_add", "terms_removal"]:
                typ3 = "publication_term"
            elif type(val) is dict or type(val) is list:
                if type(val) is dict:
                    typ3 = "dict"
                else:
                    typ3 = "list"
            else:
                typ3 = "str"
            if not (k in ["post_related_add", "post_related_removal", "terms_add", "terms_removal"] and len(val) == 0):
                if k != "meta":
                    models.Contribute.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        target_content_type=ct,
                        target_object_id=instance.id,
                        field=field,
                        value=val,
                        type=typ3,
                        status="approved" if is_authenticated else "pending"
                    )
                else:
                    for km in request.data.get(k):
                        val = request.data.get(k).get(km)
                        field = k + "__" + km
                        models.Contribute.objects.create(
                            user=request.user if request.user.is_authenticated else None,
                            target_content_type=ct,
                            target_object_id=instance.id,
                            field=field,
                            value=val,
                            type=type(val),
                            status="approved" if is_authenticated else "pending"
                        )
        return Response(
            status=status.HTTP_200_OK,
            data=caching_v2.make_post(publication.host, {"instance": instance.slug, "is_page": True}, flag)
        )
    elif request.method == "GET":
        return Response(status=status.HTTP_200_OK, data=query_post(slug, {
            "uid": request.GET.get("uid") is not None,
            "is_guess_post": request.GET.get("is_guess_post"),
            "show_cms": request.GET.get("show_cms")
        }))
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
def fetch_taxonomy_contribute(request, app_id, slug):
    if request.method == "GET":
        term = models.PublicationTerm.objects.get(pk=slug)
        if request.GET.get("fields"):
            fields = request.GET.get("fields").split(",")
        else:
            fields = ["title", "description", "meta"]
        qc = Q(target_object_id=slug, target_content_type_id=29)
        if request.GET.get("fields"):
            qc = qc & Q(field__in=request.GET.get("fields"))
        if request.GET.get("contributor"):
            qc = qc & Q(user__id=request.GET.get("contributor"))
        contrib_list = models.Contribute.objects.filter(qc).order_by("id").order_by("field").distinct("field")
        out_origin = serializers.PubTermSerializer(term).data
        out_contrib = {}
        out = {}
        for contrib in contrib_list:
            out_contrib[contrib.field] = contrib.value
        for field in fields:
            if field == "posts":
                q = Q(terms__id=slug) & ~Q(id__in=out_contrib.get("excluded_posts", []))
                if request.GET.get("contributor") is None:
                    q = q & Q(show_cms=True)
                qs = models.Post.objects.prefetch_related("terms").filter(q).values_list('id', flat=True)
                out[field] = list(map(lambda x: caching.make_post(False, None, str(x), {
                    "master": False,
                    "user": None
                }), qs))
            elif out_contrib.get(field):
                out[field] = out_contrib.get(field)
            else:
                if "meta__" in field:
                    field = field.replace("meta__", "")
                    out[field] = out_origin.get("meta").get(field)
                else:
                    out[field] = out_origin.get(field)
        return Response(status=status.HTTP_200_OK, data=out)
    elif request.method == "POST":
        for field in request.body.keys():
            models.Contribute.objects.create(
                user=request.user,
                target_object_id=slug,
                target_content_type=ContentType.objects.get(pk=29),
                field=field,
                type=type(request.body.get(field)).__name__,
                value=request.body.get(field)
            )
        return Response(status=status.HTTP_202_ACCEPTED, data="DONE")

    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


@api_view(['GET'])
def fetch_post_init(request, app_id, slug):
    action_id = get_action_id(app_id, slug, request.GET.get("uid") is not None)
    if action_id is not None:
        pass
    return Response(status=status.HTTP_200_OK, data={
        "like": {
            "is_like": False,
            "count": 0
        },
        "comment": {
            "results": [],
            "count": 0
        },
        "following": False
    })


@api_view(['GET', 'POST'])
def fetch_comments(request, app_id, slug):
    action_id = get_action_id(app_id, slug, request.GET.get("uid") is not None)
    if request.method == "GET":
        if action_id is not None:
            parent_id = request.GET.get("parent")
            user_id = request.user.id if request.user.is_authenticated else None
            p = get_paginator(request)
            with connection.cursor() as cursor:
                cursor.execute("SELECT FETCH_COMMENTS(%s, %s, %s, %s, %s, %s)", [
                    p.get("page_size"),
                    p.get("offs3t"),
                    request.GET.get("order_by"),
                    user_id,
                    parent_id,
                    action_id
                ])
                result = cursor.fetchone()[0]
                if result.get("results") is None:
                    result["results"] = []
                cursor.close()
                connection.close()
                return Response(status=status.HTTP_200_OK, data=result)
        return Response(status=status.HTTP_200_OK, data={"results": [], "count": 0})
    elif request.method == "POST":
        msg = []
        if action_id is None:
            msg.append({"action": "POST_NOT_PUBLISH"})
        if not request.user.is_authenticated:
            msg.append({"action": "AUTH_REQUIRED"})
        if request.data.get("content") is None or len(request.data.get("content")) < 2:
            msg.append({"content": "TO_SHORT"})

        if len(msg) == 0:
            c = Comment(user=request.user, activity_id=action_id, content=request.data.get("content"))
            if request.data.get("parent_comment"):
                c.parent_comment_id = request.data.get("parent_comment")
            c.save()
            return Response(status=status.HTTP_201_CREATED, data=CommentSerializer(c).data)
        return Response(status=status.HTTP_400_BAD_REQUEST, data=msg)
    else:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


@api_view(['GET'])
def fetch_contributions(request, app_id, slug):
    if request.method == "GET":
        p = get_paginator(request)
        contributor = request.GET.get("contributor")
        field = request.GET.get("field")
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_CONTRIBUTIONS(%s, %s, %s, %s, %s, %s, %s)", [
                p.get("page_size"),
                p.get("offs3t"),
                request.GET.get("order_by"),
                22,
                slug,
                contributor,
                field
            ])
            result = cursor.fetchone()[0]
            if result.get("results") is None:
                result["results"] = []
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)


@api_view(['GET', 'POST'])
def push_vote(request, app_id, slug):
    action_id = get_action_id(app_id, slug, request.GET.get("uid") is not None)
    if request.method == "GET":
        pass
    elif request.method == "POST":
        msg = []
        if action_id is None:
            msg.append({"action": "POST_NOT_PUBLISH"})
        if not request.user.is_authenticated:
            msg.append({"action": "AUTH_REQUIRED"})
        if len(msg) == 0:
            old_action = Action.objects.get(pk=action_id)
            if request.user in old_action.voters.all():
                old_action.voters.remove(request.user)
                data = False
            else:
                old_action.voters.add(request.user)
                data = True
            return Response(status=status.HTTP_202_ACCEPTED, data=data)
        return Response(status=status.HTTP_400_BAD_REQUEST, data=msg)
    else:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


@api_view(['POST', 'GET'])
def follow(request, app_id, slug):
    instance = Post.objects.get(pk=slug)
    if request.method == "GET":
        return Response({
            "is_follow": actions.is_following(request.user, instance),
            "total_follow": actions.total_following(instance)
        })
    else:
        if actions.is_following(request.user, instance):
            actions.un_follow(request.user, instance)
            flag = False
        else:
            actions.follow(request.user, instance)
            flag = True
        return Response({
            "is_follow": flag,
            "total_follow": actions.total_following(instance)
        })


@api_view(['POST', 'GET'])
def follow_term(request, app_id, slug):
    instance = PublicationTerm.objects.get(pk=slug)
    if actions.is_following(request.user, instance):
        if request.method == 'POST':
            actions.un_follow(request.user, instance)
            flag = False
        else:
            flag = True
    else:
        if request.method == 'POST':
            actions.follow(request.user, instance)
            flag = True
        else:
            flag = False
    return Response(flag)


# ==========================================================================
def fetch_instance(host_name, pk, is_pid):
    try:
        if is_pid:
            post_instance = Post.objects.get(pid=pk, primary_publication__host=host_name)
        else:
            if type(pk) == int or pk.isnumeric():
                return pk
            else:
                post_instance = Post.objects.get(slug=pk)
    except Exception as e:
        print(e)
        post_instance = None
    return post_instance.id if post_instance is not None else None


# Init
@api_view(['POST'])
def graph(request):
    hostname = request.GET.get("host", None)
    user = request.user.id if request.user.is_authenticated else None
    if hostname is None:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    if request.method == "POST":
        out = {}
        query = request.data.get("query")
        force = filter_query.query_boolean(request.GET.get("force"), False)
        for q in query:
            # INIT
            params = q.get("p") or {}
            schemas = q.get("s") or ["id"]
            instance_related = None
            instance_post_related = None
            pub_term = None
            # PREPARE
            if params.get("related"):
                instance_related = fetch_instance(hostname, params.get("related"), False)
            if params.get("post_related"):
                instance_post_related = fetch_instance(hostname, params.get("post_related"), False)
            if params.get("taxonomy") and params.get("term"):
                pub_term = models.PublicationTerm.objects.filter(
                    taxonomy=params.get("taxonomy"),
                    publication__host=hostname,
                    term__slug=params.get("term")
                ).first()
            # HANDLE QUERY
            if q.get("q") == "post_detail":
                instance = None
                if params.get("slug"):
                    instance = fetch_instance(hostname, params.get("slug"), params.get("pid"))
                out[q.get("o")] = clone_dict(
                    caching.make_post(force, hostname, instance, {"master": True}),
                    schemas, None
                )
            if q.get("q") == "post_list":
                excluded_posts = []
                if pub_term and pub_term.meta is not None:
                    excluded_posts = pub_term.meta.get("excluded_posts", None)
                page_size = params.get('page_size', 10)
                page = params.get('page', 1)
                out[q.get("o")] = clone_dict(caching.make_post_list(force, hostname, {
                    "page_size": page_size,
                    "offset": page_size * page - page_size,
                    "post_type": params.get("post_type"),
                    "post_related": instance_post_related,
                    "related": instance_related,
                    "master": True,
                    "order": params.get("order", "newest"),
                    "term": params.get("term"),
                    "taxonomy": params.get("taxonomy"),
                    "reverse": params.get("reverse"),
                    "user_id": params.get("user"),
                    "show_cms": params.get("show_cms", None),
                    "publications": params.get("publications"),
                    "excluded_posts": excluded_posts
                }), schemas, None)
            if q.get("q") == "archive":
                page_size = params.get('page_size', 10)
                page = params.get('page', 1)
                out[q.get("o")] = clone_dict(caching.make_page(force, hostname, query={
                    "post_related": instance_post_related,
                    "terms": params.get("terms"),
                    "post_type": params.get("post_type"),
                    "page_size": page_size,
                    "term_page_size": params.get("term_page_size"),
                    "offset": page_size * page - page_size,
                    "order": params.get("order", "popular"),
                    "full": params.get("full", None),
                    "is_related_expanded": params.get("expanded_related"),
                    "user_id": params.get("user"),
                    "show_cms": params.get("show_cms", None),
                    "publications": params.get("publications")
                }), schemas, None)
            if q.get("q") == "term_list":
                related = params.get("related", None)
                if related is None and params.get("related_term") and params.get("related_taxonomy"):
                    test = PublicationTerm.objects.filter(
                        publication__host=hostname,
                        term__slug=params.get("related_term"),
                        taxonomy=params.get("related_taxonomy")
                    ).first()
                    if test:
                        related = test.id
                page_size = params.get('page_size', 10)
                page = params.get('page', 1)
                out[q.get("o")] = clone_dict(caching.make_term_list(force, hostname, query={
                    "search": params.get("search"),
                    "taxonomy": params.get("taxonomy"),
                    "page_size": page_size,
                    "offset": page_size * page - page_size,
                    "order": params.get("order", "popular"),
                    "related": related,
                    "reverse": params.get("reverse", False),
                    "show_cms": params.get("show_cms", None),
                    "publications": params.get("publications"),
                    "featured": params.get("featured", None),
                }), schemas, None)
            if q.get("q") == "term_detail":
                pub_term_id = params.get("id", None)
                if pub_term_id is None:
                    if params.get("taxonomy") and params.get("term"):
                        pt = PublicationTerm.objects.filter(
                            publication__host=hostname,
                            taxonomy=params.get("taxonomy"),
                            term__slug=params.get("term")).first()
                        if pt is not None:
                            pub_term_id = pt.id
                out[q.get("o")] = clone_dict(caching.make_term(force, pub_term_id, True), schemas, None)
            if q.get("q") == "user_detail":
                out[q.get("o")] = clone_dict(query_user(params.get("user"), {}), schemas, None)
        return Response(out)


@api_view(['POST'])
def graph_v2(request):
    hostname = request.GET.get("host", None)
    if hostname is None:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    out = {}
    # type{post_list|post_detail|term_list|term_detail|user_detail|user_list}
    # params{page, page_size, order, value}
    query = request.data.get("query")
    schemas = request.data.get("schemas")
    force = filter_query.query_boolean(request.GET.get("force"), False)
    if query.get("type") == "post_list":
        out = caching_v2.make_posts(hostname, query=query, force=force)
    elif query.get("type") == "post_detail":
        out = caching_v2.make_post(hostname, {
            "instance": query.get("value"),
            "is_page": True,
            "is_pid": query.get("is_pid")
        }, force=force)
    elif query.get("type") == "term_list":
        out = caching_v2.make_terms(hostname, query=query, force=force)
    elif query.get("type") == "home":
        out = caching_v2.make_home(hostname, query=query, force=force)
    elif query.get("type") == "term_detail":
        out = caching_v2.make_term(
            hostname,
            {
                "instance": query.get("value"),
                "taxonomy": query.get("taxonomy"),
                "order": query.get("order"),
                "post_type": query.get("post_type"),
                "page": query.get("page"),
                "is_page": True
            },
            force=force
        )
    elif query.get("type") == "user_detail":
        out = caching_v2.make_user(hostname, query, force=force)
    out = clone_dict(out, schemas, None)
    return Response(out)


@api_view(['POST'])
def public_init(request, app_host):
    schema = request.data.get("schema") if request.data.get("schema") else ["id"]
    out = clone_dict({
        "p": caching.make_init(request.GET.get("force") == "true", app_host),
        "u": None
    }, schemas=schema)
    return Response(out)


# Post List - Taxonomy
@api_view(['POST'])
def public_page(request, app_host):
    schema = request.data.get("schema") if request.data.get("schema") else ["id"]
    params = request.data.get("param") or {} if request.data.get("param") is not None else {}
    page_size = params.get('page_size', 10)
    page = params.get('page', 1)
    out = caching.make_page(request.GET.get("force") == "true", app_host, query={
        "terms": params.get("terms"),
        "post_type": params.get("post_type"),
        "page_size": page_size,
        "offset": page_size * page - page_size,
        "order": params.get("order", "popular"),
        "full": params.get("full", None)
    })
    return Response(clone_dict(out, schemas=schema, out=None))


# Post Detail
@api_view(['POST'])
def public_post(request, app_host, slug):
    schema = request.data.get("schema") if request.data.get("schema") else ["id"]
    out = caching.make_post(request.GET.get("force") == "true", host_name=app_host, index=slug, query={
        "show_cms": True,
        "master": True,
        "uid": request.GET.get("uid", False)
    })
    return Response(clone_dict(out, schemas=schema, out=None))
