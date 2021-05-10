from django.db import connection
from django.db.models import Q
from django.core.cache import cache
from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
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
from utils import caching, filter_query
from django.contrib.contenttypes.models import ContentType
import json

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
                        term__slug__in=request.GET.get(tax.get("label")).split(",")
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
            "post_type": request.GET.get("post_type"),
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
        pub = Publication.objects.get(pk=app_id)
        if pub.options.get("allow_guess_post", False):
            meta = request.data.get("meta", {})
            post = Post.objects.create(
                primary_publication=pub,
                status="POSTED",
                show_cms=pub.options.get("auto_guess_public", False),
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
            if request.data.get("terms_add", None) is not None:
                prs = PublicationTerm.objects.filter(id__in=request.data.get("terms_add", []))
                for p in prs:
                    post.terms.add(p)
            return Response(
                status=status.HTTP_200_OK,
                data=caching.make_post(True, None, str(post.id), {"master": True})
            )
        return Response(status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET', 'DELETE', 'PUT'])
def fetch_post(request, app_id, slug):
    publication = Publication.objects.get(pk=app_id)
    if request.method == "PUT":
        instance = Post.objects.get(pk=slug)
        is_authenticated = request.user.is_authenticated and request.user.is_superuser or request.user.is_staff or request.user is instance.user
        if is_authenticated:
            if request.data.get("title"):
                instance.title = request.data.get("title")
            if request.data.get("show_cms"):
                instance.show_cms = request.data.get("show_cms")
            if request.data.get("description"):
                instance.description = request.data.get("description")
            if request.data.get("content"):
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
            if request.data.get("terms_add"):
                for p in request.data.get("terms_add"):
                    pr = PublicationTerm.objects.get(pk=p)
                    instance.terms.add(pr)
            instance.save()
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
                    for km in request.data.get("meta"):
                        val = request.data.get("meta").get(km)
                        if type(val) is dict or type(val) is list:
                            if type(val) is dict:
                                typ3 = "dict"
                            else:
                                typ3 = "list"
                        else:
                            typ3 = "str"

                        field = k + "__" + km
                        models.Contribute.objects.create(
                            user=request.user if request.user.is_authenticated else None,
                            target_content_type=ct,
                            target_object_id=instance.id,
                            field=field,
                            value=val,
                            type=typ3,
                            status="approved" if is_authenticated else "pending"
                        )
        return Response(
            status=status.HTTP_200_OK,
            data=caching.make_post(True, None, str(instance.id), {"master": True})
        )

    if request.method in ["GET"]:
        return Response(status=status.HTTP_200_OK, data=query_post(slug, {
            "uid": request.GET.get("uid") is not None,
            "is_guess_post": request.GET.get("is_guess_post"),
            "show_cms": request.GET.get("show_cms")
        }))
    return Response(status=status.HTTP_204_NO_CONTENT)


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

            # PREPARE
            if params.get("related"):
                instance_related = fetch_instance(hostname, params.get("related"), False)
            if params.get("post_related"):
                instance_post_related = fetch_instance(hostname, params.get("post_related"), False)

            # HANDLE QUERY
            if q.get("q") == "post_detail":
                instance = None
                if params.get("slug"):
                    instance = fetch_instance(hostname, params.get("slug"), params.get("pid"))
                if user:
                    out[q.get("o")] = clone_dict(query_post(instance, {"user": user}), schemas, None)
                else:
                    out[q.get("o")] = clone_dict(
                        caching.make_post(force, hostname, instance, {"master": True}),
                        schemas, None
                    )
            if q.get("q") == "post_list":
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
                    "reverse": params.get("reverse"),
                    "user_id": params.get("user"),
                    "show_cms": params.get("show_cms", None),
                    "publications": params.get("publications")
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
                    "publications": params.get("publications")
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
