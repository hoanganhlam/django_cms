import json
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
from apps.cms.models import Post, Publication, Term
from apps.cms.api import serializers
from apps.authentication.api.serializers import UserSerializer
from apps.cms import models
from apps.activity.models import Comment, Action
from apps.activity.api.serializers import CommentSerializer
from utils.other import get_paginator

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
    action_id = None
    if post is not None:
        if post.options is None:
            post.options = {}
        action_id = post.options.get("action_post")
        if action_id is None and post.status == "POSTED":
            new_action = action.send(
                post.user,
                verb=verbs.POST_CREATED,
                action_object=post,
                target=post.primary_publication if post.primary_publication is not None else None
            )
            action_id = new_action[0][1].id
            post.options['action_post'] = action_id
            post.save()
    return action_id


def clone_dict(dct, schemas, out=None):
    if out is None:
        if type(dct) == dict:
            out = {}
        if type(dct) == list:
            out = []
    if type(dct) == dict:
        for schema in schemas:
            if type(schema) == dict:
                k = list(schema.keys())[0]
                out[k] = clone_dict(dct.get(k), schema[k], None)
            elif type(schema) == str:
                out[schema] = dct.get(schema)
    elif type(dct) == list:
        for d in dct:
            out.append(clone_dict(d, schemas, None))
    return out


def query_posts(q):
    with connection.cursor() as cursor:
        meta = json.loads(q.get("meta")) if q.get("meta") else None
        cursor.execute("SELECT FETCH_POSTS(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                       [
                           q.get("page_size"),
                           q.get("offs3t"),
                           q.get("search"),
                           q.get("order_by"),
                           q.get("user_id"),
                           q.get("type"),
                           q.get("status"),
                           q.get("is_guess_post", False),
                           q.get("show_cms", True),
                           q.get("taxonomies_operator", "OR"),
                           '{' + q.get('taxonomies') + '}' if q.get('taxonomies') else None,
                           '{' + q.get('app_id') + '}' if q.get('app_id') else None,
                           q.get("related_operator", "OR"),
                           '{' + q.get('post_related') + '}' if q.get('post_related') else None,
                           json.dumps(meta) if meta else None
                       ])
        result = cursor.fetchone()[0]
        if result.get("results") is None:
            result["results"] = []
        cursor.close()
        return result


def query_post(slug, q):
    with connection.cursor() as cursor:
        cursor.execute("SELECT FETCH_POST(%s, %s, %s, %s)", [
            int(slug) if slug.isnumeric() else slug,
            q.get("uid"),
            q.get("is_guess_post"),
            q.get("show_cms")
        ])
        result = cursor.fetchone()[0]
        cursor.close()
        return result


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
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_PUBLICATION(%s, %s)", [
                request.GET.get("host"),
                request.user.id if request.user.is_authenticated else None
            ])
            result = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)


@api_view(['POST'])
def graph(request):
    if request.method == "POST":
        out = {}
        path = request.data.get("path")
        query = request.data.get("query")
        force = request.GET.get("force", False)
        if path and path in cache and force is False:
            out = cache.get(path)
        else:
            user_id = request.user.id if request.user.is_authenticated else None
            for q in query:
                params = q.get("p") or {}
                # for k in params.keys():
                #     if type(params[k]) == dict and params[k].get("type") == "relation" and params[k].get("fields"):
                #         temp = out
                #         for f in params[k].get("fields"):
                #             if temp and type(temp) == dict:
                #                 temp = temp.get(f)
                #         params[k] = temp
                schemas = q.get("s") or ["id"]
                if q.get("q") == "post_detail":
                    temp = query_post(params.get("slug"), {
                        "uid": params.get("uid"),
                        "is_guess_post": params.get("is_guess_post"),
                        "show_cms": params.get("show_cms")
                    })
                    out[q.get("o")] = clone_dict(temp, schemas, None)
                if q.get("q") == "post_list":
                    page_size = params.get('page_size', 10)
                    page = params.get('page', 1)
                    offs3t = page_size * page - page_size
                    out[q.get("o")] = clone_dict(query_posts({
                        "page_size": page_size,
                        "offs3t": offs3t,
                        "search": params.get("search"),
                        "order_by": params.get("order_by"),
                        "user_id": user_id,
                        "type": params.get("type"),
                        "status": params.get("status"),
                        "is_guess_post": params.get("is_guess_post"),
                        "show_cms": params.get("show_cms", None),
                        "taxonomies_operator": params.get("taxonomies_operator"),
                        "taxonomies": params.get('taxonomies'),
                        "app_id": params.get("app"),
                        "related_operator": params.get("related_operator"),
                        "post_related": params.get("post_related"),
                        "meta": params.get("meta")
                    }), schemas, None)
            new_path = path
            if "&force=true" in path:
                new_path = path.replace("&force=true", "")
            elif "?force=true" in path:
                new_path = path.replace("?force=true", "")
            cache.set(new_path, out, timeout=CACHE_TTL)
        return Response(out)


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
                title=request.data.get("title"),
                description=request.data.get("description"),
                content=request.data.get("content"),
                primary_publication=pub,
                status="POSTED",
                post_type=request.data.get("post_type"),
                user=request.user if request.user.is_authenticated else None,
                meta=meta,
                show_cms=pub.options.get("auto_guess_public", False),
                is_guess_post=True
            )
            if request.data.get("post_related", None) is not None:
                for p in request.data.get("post_related", None):
                    pr = Post.objects.get(pk=p)
                    post.post_related.add(pr)
            with connection.cursor() as cursor:
                cursor.execute("SELECT FETCH_POST(%s, %s, %s, %s)", [
                    post.id,
                    request.GET.get("uid") is not None,
                    None,
                    None
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
            return Response(status=status.HTTP_400_BAD_REQUEST, data=data)
        return Response(status=status.HTTP_400_BAD_REQUEST, data=msg)
    else:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
