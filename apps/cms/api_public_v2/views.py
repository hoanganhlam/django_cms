from . import serializers
from apps.cms import models
from apps.activity.models import Comment, Action
from apps.activity.api.serializers import CommentSerializer
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import connection
from django.db.models import Q
from utils.other import get_paginator
from apps.activity import verbs, action


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
                               '{' + app_id + '}',
                           ])
            result = cursor.fetchone()[0]
            if result.get("results") is None:
                result["results"] = []
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)


@api_view(['GET', 'DELETE', 'PUT'])
def fetch_taxonomy(request, app_id, slug):
    tax = models.TermTaxonomy.objects.filter(term__slug=slug, taxonomy=request.GET.get("taxonomy")).first()
    return Response(serializers.TermTaxonomySerializer(tax).data)


@api_view(['GET', 'POST'])
def fetch_posts(request, app_id):
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
                               '{' + app_id + '}',
                           ])
            result = cursor.fetchone()[0]
            if result.get("results") is None:
                result["results"] = []
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)


@api_view(['GET', 'DELETE', 'PUT'])
def fetch_post(request, app_id, slug):
    if request.method == "GET":
        with connection.cursor() as cursor:
            cursor.execute("SELECT FETCH_POST(%s, %s)", [
                int(slug) if slug.isnumeric() else slug,
                request.GET.get("uid") is not None
            ])
            result = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            return Response(status=status.HTTP_200_OK, data=result)


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
            return Response(status=status.HTTP_400_BAD_REQUEST, data=CommentSerializer(c).data)
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
            action = Action.objects.get(pk=action_id)

            if request.user in action.voters.all():
                action.voters.remove(request.user)
                data = False
            else:
                action.voters.add(request.user)
                data = True
            return Response(status=status.HTTP_400_BAD_REQUEST, data=data)
        return Response(status=status.HTTP_400_BAD_REQUEST, data=msg)
    else:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
