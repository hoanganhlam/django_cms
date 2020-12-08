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
from utils.query import query_post, query_posts, query_publication
from utils import caching

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


# ==========================================================================
@api_view(['GET'])
def init(request):
    if request.method == "GET":
        user = None
        if request.user.is_authenticated:
            with connection.cursor() as cursor:
                cursor.execute("SELECT FETCH_USER_BY_USERNAME(%s, %s)", [
                    request.user.username,
                    request.user.id if request.user.is_authenticated else None
                ])
                user = cursor.fetchone()[0]
        with connection.cursor() as cursor:
            print(request.GET.get("host"))
            cursor.execute("SELECT FETCH_PUBLICATION(%s, %s)", [
                request.GET.get("host"),
                request.user.id if request.user.is_authenticated else None
            ])
            result = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data={
                "p": result,
                "u": user
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
                               app_id,
                           ])
            result = cursor.fetchone()[0]
            if result.get("results") is None:
                result["results"] = []
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)


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
    return Response()


@api_view(['GET', 'POST'])
def fetch_posts(request, app_id):
    if request.method == "GET":
        # print(request.META['QUERY_STRING'])
        app = models.Publication.objects.get(pk=app_id)
        if app.options is None:
            app.options = {}
        tax_list = app.options.get("taxonomies")
        term_ids = []
        if tax_list:
            for tax in tax_list:
                if request.GET.get(tax.get("label")):
                    qs = models.PublicationTerm.objects.filter(
                        publication=app,
                        taxonomy=tax.get("label"),
                        term__slug=request.GET.get(tax.get("label"))
                    )
                    for s in qs:
                        term_ids.append(str(s.id))
        p = get_paginator(request)
        user_id = request.user.id if request.user.is_authenticated else None
        return Response(status=status.HTTP_200_OK, data=query_posts({
            "page_size": p.get("page_size"),
            "offs3t": p.get("offs3t"),
            "search": p.get("search"),
            "order_by": request.GET.get("order_by"),
            "user_id": user_id,
            "type": request.GET.get("type"),
            "status": "POSTED",
            "is_guess_post": request.GET.get("is_guess_post"),
            "show_cms": request.GET.get("show_cms", None),
            "taxonomies_operator": request.GET.get("taxonomies_operator"),
            "taxonomies": "".join(term_ids),
            "app_id": app_id,
            "related_operator": request.GET.get("related_operator"),
            "post_related": request.GET.get('post_related'),
            "meta": request.GET.get("meta")
        }))
    if request.method == "POST":
        err = []
        if request.data.get("publications", None) is None or len(request.data.get("publications", None)) == 0:
            err.append("ERR_PUBLICATION")
        if len(err):
            return Response(data=err, status=status.HTTP_400_BAD_REQUEST)
        pub = Publication.objects.get(pk=request.data.get("publications")[0])
        if pub.options.get("allow_guess_post", False):
            meta = request.data.get("meta", {})
            meta["price"] = request.data.get("price", 0)
            post = Post.objects.create(
                title=request.data.get("title", "Untitled"),
                description=request.data.get("description"),
                content=request.data.get("content"),
                primary_publication=pub,
                status="POSTED",
                post_type=request.data.get("post_type", "article"),
                user=request.user if request.user.is_authenticated else None,
                meta=meta,
                show_cms=pub.options.get("auto_guess_public", False),
                is_guess_post=True
            )
            if request.data.get("post_related", None) is not None:
                for p in request.data.get("post_related", None):
                    pr = Post.objects.get(pk=p)
                    post.post_related.add(pr)
            if request.data.get("terms", None) is not None:
                prs = PublicationTerm.objects.filter(id__in=request.data.get("terms", []))
                for p in prs:
                    post.terms.add(p)
            with connection.cursor() as cursor:
                cursor.execute("SELECT FETCH_POST(%s, %s, %s, %s, %s)", [
                    post.id,
                    request.GET.get("uid") is not None,
                    None,
                    None,
                    request.user.id
                ])
                result = cursor.fetchone()[0]
                cursor.close()
                connection.close()
                return Response(status=status.HTTP_200_OK, data=result)
        return Response(status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET', 'DELETE', 'PUT'])
def fetch_post(request, app_id, slug):
    if request.method == "GET":
        return Response(status=status.HTTP_200_OK, data=query_post(slug, {
            "uid": request.GET.get("uid") is not None,
            "is_guess_post": request.GET.get("is_guess_post"),
            "show_cms": request.GET.get("show_cms")
        }))


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


@api_view(['POST'])
def follow(request, app_id, slug):
    instance = Post.objects.get(pk=slug)
    if actions.is_following(request.user, instance):
        actions.un_follow(request.user, instance)
        flag = False
    else:
        actions.follow(request.user, instance)
        flag = True
    return Response(flag)


# ==========================================================================
# Init
@api_view(['POST'])
def graph(request):
    hostname = request.GET.get("host", None)
    user = request.user.id if request.user.is_authenticated else None
    pub = Publication.objects.get(host=hostname) if user else None
    if hostname is None:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    if request.method == "POST":
        out = {}
        query = request.data.get("query")
        force = request.GET.get("force", False)
        for q in query:
            params = q.get("p") or {}
            schemas = q.get("s") or ["id"]
            if q.get("q") == "post_detail":
                if user:
                    out[q.get("o")] = clone_dict(query_post(params.get("slug"), {
                        "user": user
                    }), schemas, None)
                else:
                    out[q.get("o")] = clone_dict(caching.make_post(force, hostname, params.get("slug"), {
                        "master": True
                    }), schemas, None)
            if q.get("q") == "post_list":
                page_size = params.get('page_size', 10)
                page = params.get('page', 1)
                if user:
                    out[q.get("o")] = clone_dict(query_posts({
                        "page_size": page_size,
                        "offs3t": page_size * page - page_size,
                        "search": params.get("search"),
                        "order_by": params.get("order_by"),
                        "user_id": user,
                        "type": params.get("type"),
                        "status": "POSTED",
                        "is_guess_post": params.get("is_guess_post"),
                        "show_cms": params.get("show_cms", None),
                        "taxonomies_operator": params.get("taxonomies_operator"),
                        "taxonomies": None,
                        "app_id": str(pub.id),
                        "related_operator": params.get("related_operator"),
                        "post_related": params.get('post_related'),
                        "related": params.get("related"),
                        "meta": params.get("meta"),
                        "term": params.get("term"),
                    }), schemas, None)
                else:
                    out[q.get("o")] = clone_dict(caching.make_post_list(force, hostname, {
                        "page_size": page_size,
                        "offset": page_size * page - page_size,
                        "post_type": params.get("post_type"),
                        "post_related": params.get("post_related"),
                        "master": True,
                        "related": params.get("related"),
                        "order": params.get("order", "newest"),
                        "term": params.get("term"),
                    }), schemas, None)
            if q.get("q") == "archive":
                page_size = params.get('page_size', 10)
                page = params.get('page', 1)
                out[q.get("o")] = clone_dict(caching.make_page(force, hostname, query={
                    "post_related": params.get("post_related"),
                    "terms": params.get("terms"),
                    "post_type": params.get("post_type"),
                    "page_size": page_size,
                    "offset": page_size * page - page_size,
                    "order": params.get("order", "popular"),
                    "full": params.get("full", None)
                }), schemas, None)
            if q.get("q") == "term_list":
                page_size = params.get('page_size', 10)
                page = params.get('page', 1)
                out[q.get("o")] = clone_dict(caching.make_term_list(force, hostname, query={
                    "taxonomy": params.get("taxonomy"),
                    "page_size": page_size,
                    "offset": page_size * page - page_size,
                    "order": params.get("order", "popular")
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
        "term": params.get("term"),
        "taxonomy": params.get("taxonomy"),
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
