from django.core.cache import cache
from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.db.models import Q
from . import query as query_maker
from apps.cms.models import Term, Post
from apps.cms.api.serializers import TermSerializer

CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)


def make_init(force, host_name):
    if host_name not in cache or force:
        out = query_maker.query_publication(host_name)
        cache.set(host_name, out, timeout=CACHE_TTL)
    else:
        out = cache.get(host_name)
    return out


def make_page(force, host_name, query, **kwargs):
    key_path = host_name + "_page"
    q = Q(primary_publication__host=host_name) | Q(publications__host=host_name)
    taxonomy = query.get("taxonomy")
    post_type = query.get("post_type")
    term = query.get("term")
    # ====================================================================================
    if taxonomy is not None:
        q = q & Q(terms__taxonomy=taxonomy)
        key_path = "{}_{}".format(key_path, taxonomy)
    if term is not None:
        q = q & Q(terms__term__slug=term)
        key_path = "{}_{}".format(key_path, term)
    if post_type is not None:
        q = q & Q(post_type=post_type)
        key_path = "{}_{}".format(key_path, post_type)
    # ====================================================================================
    if key_path not in cache or force:
        term_object = Term.objects.filter(slug=term).first() if term is not None else None
        newest = list(Post.objects.filter(q).order_by("-id").values_list('id', flat=True))
        popular = list(Post.objects.filter(q).order_by("id").values_list('id', flat=True))
        terms = Term.objects.filter(pub_terms__publication__host=host_name)[:10]
        out = {
            "term": TermSerializer(term_object).data,  # const
            "newest": {
                "results": newest,
                "count": len(newest)
            },
            "popular": {
                "results": popular,
                "count": len(popular)
            },
            "terms": TermSerializer(terms, many=True).data  # const
        }
        cache.set(key_path, out, timeout=60 * 60 * 24)
    else:
        out = cache.get(key_path)
    # ====================================================================================
    start = query.get("offset", 0)
    end = query.get("offset", 0) + query.get("page_size", 10)
    order = query.get("order", "popular")
    out[order]["results"] = list(map(lambda x: make_post(force, "", str(x), {
        "master": True
    }), out[order]["results"][start: end]))
    for flag in ["newest", "popular"]:
        if flag != order:
            if query.get("full"):
                out[flag]["results"] = list(
                    map(lambda x: make_post(force, "", str(x), {"master": True}), out[flag]["results"][: 5]))
            else:
                out[flag]["results"] = []
    # ====================================================================================
    return out


def make_post(force, host_name, index, query):
    if index is None or type(index) != str:
        return None
    key_path = "{}_{}".format("post", index)
    if force or key_path not in cache:
        data = query_maker.query_post(slug=index, query=query)
        cache.set(key_path, data, timeout=CACHE_TTL)
    else:
        data = cache.get(key_path)
    if query.get("master", False) is True:
        data["next"] = make_post(force, host_name, str(data.get("next")), {}) if type(data.get("next")) is int else None
        data["previous"] = make_post(force, host_name, str(data.get("previous")), {}) if type(
            data.get("previous")) is int else None
        print(data["related"])
        data["related"] = list(
            filter(lambda x: x,
                   map(
                       lambda x: make_post(force, "", str(x.get("id")) if x else None, {}),
                       data.get("related") if data.get("related") else []
                   )
                   )
        )
    return data
