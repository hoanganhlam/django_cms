import json
from django.db import connection


def query_posts(q):
    with connection.cursor() as cursor:
        meta = json.loads(q.get("meta")) if q.get("meta") else None
        cursor.execute("SELECT FETCH_POSTS_X(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                       [
                           q.get("page_size"),
                           q.get("offs3t"),
                           q.get("search"),
                           q.get("order_by"),
                           q.get("auth_id"),
                           q.get("post_type"),
                           q.get("status"),
                           q.get("is_guess_post", False),
                           q.get("show_cms", True),
                           q.get("taxonomies_operator", "OR"),
                           '{' + q.get('taxonomies') + '}' if q.get('taxonomies') else None,
                           '{' + q.get('app_id') + '}' if q.get('app_id') else None,
                           q.get("related_operator", "OR"),
                           '{' + str(q.get('post_related')) + '}' if q.get('post_related') else None,
                           q.get("related"),
                           json.dumps(meta) if meta else None
                       ])
        result = cursor.fetchone()[0]
        if result.get("results") is None:
            result["results"] = []
        cursor.close()
        return result


def query_post(slug, query):
    with connection.cursor() as cursor:
        cursor.execute("SELECT FETCH_POST(%s, %s, %s, %s, %s)", [
            int(slug) if type(slug) is int or (type(slug) is str and slug.isnumeric()) else slug,
            query.get("pid"),
            query.get("is_guess_post"),
            query.get("show_cms"),
            query.get("user")
        ])
        result = cursor.fetchone()[0]
        cursor.close()
        return result


def query_post_detail(pk):
    with connection.cursor() as cursor:
        cursor.execute("SELECT FETCH_POST_DETAIL(%s)", [pk])
        result = cursor.fetchone()[0]
        cursor.close()
        return result


def query_term(pk):
    with connection.cursor() as cursor:
        cursor.execute("SELECT FETCH_TAXONOMY_BY_ID(%s)", [pk])
        result = cursor.fetchone()[0]
        cursor.close()
        return result


def query_term_tax(taxonomy, term, pub_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT FETCH_TAXONOMY(%s, %s, %s)", [
            term,
            pub_id,
            taxonomy,
        ])
        result = cursor.fetchone()[0]
        cursor.close()
        return result


def query_publication(host):
    with connection.cursor() as cursor:
        cursor.execute("SELECT FETCH_PUBLICATION(%s, %s)", [
            host,
            None
        ])
        result = cursor.fetchone()[0]
        cursor.close()
        connection.close()
        return result


def query_related(q):
    with connection.cursor() as cursor:
        cursor.execute("SELECT FETCH_RELATED_POST(%s, %s, %s)", [q.get("id"), q.get("post_type"), q.get("limit")])
        result = cursor.fetchone()[0]
        if result is None:
            result = []
        return list(map(lambda x: x.get("id"), result))


def query_user(username, query):
    with connection.cursor() as cursor:
        if type(username) is str:
            cursor.execute("SELECT FETCH_USER_BY_USERNAME(%s, %s)", [
                username,
                query.get("auth_id")
            ])
        else:
            cursor.execute("SELECT FETCH_USER_ID(%s)", [
                username
            ])
        result = cursor.fetchone()[0]
        cursor.close()
        return result


def query_user_id(username, query):
    with connection.cursor() as cursor:
        if type(username) is str:
            cursor.execute("SELECT FETCH_USER_BY_USERNAME(%s, %s)", [
                username,
                query.get("auth_id")
            ])
        else:
            cursor.execute("SELECT FETCH_USER_ID(%s)", [
                username
            ])
        result = cursor.fetchone()[0]
        cursor.close()
        return result