from django.db.models import Q
from django.core.cache import cache
from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from apps.cms.models import Post, PublicationTerm, Publication
from utils import query as query_maker

CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)


# HELPER
def check_page_size(theme, flag, field, default=10):
    if theme and theme.get(flag) and theme.get(flag).get(field):
        return theme.get(flag).get(field)
    return default


def get_post_type_related(pub, post_type):
    if type(pub) is str:
        pub = maker_pub(pub, False)
    post_types = pub.get("options").get("post_types")
    filtered = next((x for x in post_types if x.get("label") == post_type), None)
    return filtered.get("related") or []


def maker_pub(hostname, force):
    key_path = "{}_{}".format("pub", hostname)
    if force or key_path not in cache:
        data = query_maker.query_publication(hostname)
        cache.set(key_path, data)
    else:
        data = cache.get(key_path)
        if type(data) is Publication:
            data = query_maker.query_publication(hostname)
            cache.set(key_path, data)
    return data


def make_post(hostname, query, force):
    pk = query.get("instance")
    key_path = "post-{post_id}".format(post_id=pk)
    if force or key_path not in cache:
        data = query_maker.query_post_detail(slug=pk)
        post_type_related = get_post_type_related(hostname, data.get("post_type"))
        ide = data.get("id")
        for pt in post_type_related:
            q = Q(primary_publication__host=hostname,
                  post_related_revert__slug=pk,
                  show_cms=True,
                  post_type=pt) & (Q(post_related_revert__id=ide) | Q(post_related__id=ide))
            data[pt] = list(Post.objects.prefetch_related("post_related", "post_related_revert")
                            .filter(q)
                            .values_list("id", flat=True))
        cache.set(key_path, data, timeout=CACHE_TTL)
    else:
        data = cache.get(key_path)
    if query.get("is_page"):
        pub = maker_pub(hostname, False)
        post_type_related = get_post_type_related(pub, data.get("post_type"))
        limit_list_related = check_page_size(pub.get("theme"), "general", "limit_list_related", 5)
        data["related"] = list(
            map(
                lambda x: make_post(hostname, {"instance": str(x)}, False),
                data.get("related")[0: limit_list_related]))
        for pt in post_type_related:
            data[pt] = {
                "results": list(
                    map(
                        lambda x: make_post(hostname, {"instance": str(x)}, False),
                        data.get(pt, [])[0: limit_list_related])),
                "count": len(data.get(pt, []))
            }
    data["user"] = make_user(hostname, {"value": data.get("user_id")}, False).get("instance") if data.get(
        "user_id") else None
    data["terms"] = list(
        map(lambda x: make_term(hostname, {"instance": x}, False).get("instance"), data.get("terms", []))) if data.get("terms") else []
    return data


def make_posts(hostname, query, force):
    pub = maker_pub(hostname, False)
    page = query.get("page", 1)
    page_size = check_page_size(pub.get("theme"), "general", "post_limit", 10)
    offset = page_size * page - page_size
    post_type = query.get("post_type") or pub.options.get("default_post_type", "article")
    order = query.get("order") or "p"  # n-newest|p-popular|d-daily
    key_path = "{}_{}_{}".format(hostname, post_type, order)
    if force or key_path not in cache:
        pub_instance = Publication.objects.get(pk=pub.get("id"))
        ids = pub_instance.make_posts(post_type, order)
    else:
        ids = cache.get(key_path)
    return {
        "results": list(
            map(lambda x: make_post(hostname, {"instance": str(x)}, False), ids[offset: offset + page_size])),
        "count": len(ids)
    }


def make_term(hostname, query, force):
    instance = query.get("instance")
    if type(instance) is PublicationTerm:
        pk = instance.id
    elif type(instance) is dict:
        pk = instance.get("id")
    else:
        pk = instance
    key_path = "{}_{}".format("term", pk)
    if force or key_path not in cache:
        data = query_maker.query_term(pk=pk)
        cache.set(key_path, data)
    else:
        data = cache.get(key_path)
    if query.get("is_page") and type(instance) is PublicationTerm:
        page = query.get("page") or 1
        order = query.get("order") or "n"
        post_type = query.get("post_type") or "article"
        key_path_post = "term_{}_{}_{}".format(instance.id, post_type, order)
        pub = maker_pub(hostname, False)
        page_size = check_page_size(pub.get("theme"), "general", "post_limit", 10)
        limit_list_related = check_page_size(pub.get("theme"), "general", "limit_list_related", 5)
        offset = page_size * page - page_size
        if force or key_path_post not in cache:
            ids = instance.make_posts(query.get("post_type", "article"), order)
        else:
            ids = cache.get(key_path_post)
        if data.get("related"):
            data["related"] = list(
                map(lambda x: make_term(hostname, {"instance": x}, False), data.get("related")[0: limit_list_related]))
    else:
        ids = []
        offset = 0
        page_size = 0
    return {
        "instance": data,
        "post_response": {
            "results": list(
                map(lambda x: make_post(hostname, {"instance": str(x)}, False), ids[offset: offset + page_size])),
            "count": len(ids)
        }
    }


def make_terms(hostname, query, force):
    pub = maker_pub(hostname, force)
    page = query.get("page") or 1
    page_size = check_page_size(pub.get("theme"), "general", "term_limit", 10)
    taxonomy = query.get("taxonomy") or pub.options.get("default_taxonomy", "category")
    order = query.get("order") or "p"  # n-newest|p-popular|d-daily
    key_path = "{}_{}_{}".format(hostname, taxonomy, order)
    if force or key_path not in cache:
        pub_instance = Publication.objects.get(pk=pub.get("id"))
        ids = pub_instance.maker_terms(taxonomy, order)
    else:
        ids = cache.get(key_path)
    offset = page_size * page - page_size
    return {
        "results": list(map(lambda x: make_term(hostname, {"instance": x}, False).get("instance"),
                            ids[offset: offset + page_size])),
        "count": len(ids)
    }


def make_user(hostname, query, force):
    pk = query.get("value")
    key_path = "user_{}".format(hostname, pk)
    if force or key_path not in cache:
        data = query_maker.query_user(pk, {})
        cache.set(key_path, data)
    else:
        data = cache.get(key_path)
    if query.get("is_page"):
        post_type = query.get("post_type", "article")
        order = query.get("order", "n")
        key_path_post = "{}_user_{}_{}_{}".format(
            hostname,
            pk,
            post_type,
            order
        )
        page = query.get("page", 1)
        page_size = query.get("page_size", 10)
        offset = page_size * page - page_size
        if force or key_path_post not in cache:
            ids = Post.objects.filter(
                post_related_revert__primary_publication__host=hostname,
                user_id=pk,
                post_type=post_type).distinct().values_list('id', flat=True)
        else:
            ids = cache.get(key_path_post)
    else:
        ids = []
        offset = 0
        page_size = 0
    return {
        "instance": data,
        "post_response": {
            "results": list(map(lambda x: make_post(hostname, str(x), False), ids[offset: offset + page_size])),
            "count": len(ids)
        }
    }


def make_home(hostname, query, force):
    return {
        "response_post": make_posts(hostname, query, force),
        "response_term": make_terms(hostname, query, force)
    }
