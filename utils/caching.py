from django.core.cache import cache
from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.db.models import Q
from . import query as query_maker
from apps.cms.models import Term, Post, PublicationTerm, Publication
from apps.cms.api.serializers import TermSerializer, PubTermSerializer

CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)


def make_init(force, host_name):
    if host_name not in cache or force:
        out = query_maker.query_publication(host_name)
        cache.set(host_name, out, timeout=CACHE_TTL)
    else:
        out = cache.get(host_name)
    return out


def make_page(force, host_name, query, **kwargs):
    term_term = None
    term_taxonomy = None
    key_path = host_name + "_page"
    # ====================================================================================
    q_term = Q(publication__host=host_name)
    q = Q(primary_publication__host=host_name) | Q(publications__host=host_name)
    if query.get("publications"):
        q = q | Q(primary_publication__id__in=query.get("publications"))
    q = q & Q(status="POSTED")
    # ====================================================================================
    post_type = query.get("post_type")
    post_related = query.get("post_related")
    post_terms = query.get("terms", {})
    post_terms_keys = list(post_terms.keys())
    user = query.get("user_id")
    show_cms = query.get("show_cms", None)
    if len(post_terms_keys) == 1:
        term_taxonomy = post_terms_keys[0]
        term_term = post_terms.get(term_taxonomy, None)
    # ====================================================================================
    if show_cms is not None:
        q_term = q_term & Q(show_cms=show_cms)
        q = q & Q(show_cms=show_cms)
        key_path = "{}_show_cms-{}".format(key_path, show_cms)
    if term_taxonomy is not None:
        q_term = q_term & Q(taxonomy=term_taxonomy)
        q = q & Q(terms__taxonomy=term_taxonomy)
        key_path = "{}_{}".format(key_path, term_taxonomy)
    if term_term is not None:
        q = q & Q(terms__term__slug=term_term)
        key_path = "{}_{}".format(key_path, term_term)
    if post_type is not None:
        q = q & Q(post_type=post_type)
        key_path = "{}_{}".format(key_path, post_type)
    if post_related is not None:
        q = q & Q(post_related__id=post_related)
        key_path = "{}_post_related-{}".format(key_path, post_related)
    if user is not None:
        q = q & Q(user__username=user)
        key_path = "{}_user-{}".format(key_path, user)
    # ====================================================================================
    if key_path not in cache or force:
        term_object = PublicationTerm.objects.filter(term__slug=term_term, taxonomy=term_taxonomy).first() if term_term is not None else None
        newest = list(Post.objects.filter(q).order_by("-id").values_list('id', flat=True))
        popular = list(Post.objects.filter(q).order_by("-measure__score").values_list('id', flat=True))
        terms = PublicationTerm.objects.filter(q_term)[:12].values_list("id", flat=True)
        out = {
            "term": term_object.id if term_object is not None else None,
            "newest": {
                "results": newest,
                "count": len(newest)
            },
            "popular": {
                "results": popular,
                "count": len(popular)
            },
            "terms": terms
        }
        cache.set(key_path, out, timeout=60 * 60 * 24)
    else:
        out = cache.get(key_path)
    # ====================================================================================
    start = query.get("offset", 0)
    end = query.get("offset", 0) + query.get("page_size", 10)
    order = query.get("order", "popular")
    out[order]["results"] = list(map(lambda x: make_post(False, host_name, str(x), {
        "master": True
    }), out[order]["results"][start: end]))
    for flag in ["newest", "popular"]:
        if flag != order:
            if query.get("full"):
                out[flag]["results"] = list(
                    map(lambda x: make_post(False, host_name, str(x), {"master": True}), out[flag]["results"][: 5]))
            else:
                out[flag]["results"] = []
    if out.get("term", None) is not None:
        out["term"] = make_term(False, out["term"], False)
        if query.get("is_related_expanded") and out["term"].get("related") is not None:
            out["term"]["related"] = list(map(lambda x: make_term(False, x, False), out["term"]["related"]))
    out["terms"] = list(map(lambda x: make_term(False, x), out["terms"]))[:query.get("term_page_size", 10)]
    # ====================================================================================
    return out


def make_post(force, host_name, index, query):
    if index is None:
        return None
    q_general = Q(primary_publication__host=host_name) | Q(publications__host=host_name)
    q_general = q_general & Q(show_cms=True, status="POSTED")
    key_path = "{post_type}-{id}".format(post_type="post", id=index)
    if force or key_path not in cache:
        data = query_maker.query_post(slug=index, query=query)
        n = Post.objects.filter(q_general, id__gt=data.get("id")).first()
        p = Post.objects.filter(q_general, id__lt=data.get("id")).first()
        data["next"] = n.id if n is not None else None
        data["previous"] = p.id if p is not None else None
        cache.set(key_path, data, timeout=CACHE_TTL)
    else:
        data = cache.get(key_path)
    if query.get("master", False) is True:
        data["next"] = make_post(False, host_name, str(data.get("next")), {}) if type(data.get("next")) is int else None
        data["previous"] = make_post(False, host_name, str(data.get("previous")), {}) if type(
            data.get("previous")) is int else None
    return data


def make_post_list(force, host_name, query):
    order = query.get("order")
    key_path = host_name + "_list_" + order
    post_type = query.get("post_type")
    related = query.get("related")
    post_related = query.get("post_related")
    term = query.get("term")
    user = query.get("user_id")
    show_cms = query.get("show_cms")
    # Check query.get("publications")
    q = Q(primary_publication__host=host_name) | Q(publications__host=host_name)
    if query.get("publications"):
        q = q | Q(primary_publication__id__in=query.get("publications"))
    q = q & Q(status="POSTED")
    if show_cms is not None:
        q = q & Q(show_cms=show_cms)
        key_path = "{}_cms-{}".format(key_path, show_cms)
    # Related outer
    if related is not None:
        key_path = "{}_related-{}".format(key_path, related)
        order = "popular"
    # Related inner
    if user is not None:
        q = q & Q(user__id=user)
        key_path = "{}_user-{}".format(key_path, user)
    if post_related is not None:
        if query.get("reverse"):
            q = q & Q(post_related_revert__id=post_related)
            key_path = "{}_post_related_revert-{}".format(key_path, post_related)
        else:
            q = q & Q(post_related__id=post_related)
            key_path = "{}_post_related-{}".format(key_path, post_related)
    if post_type is not None:
        q = q & Q(post_type=post_type)
        key_path = "{}_post_type-{}".format(key_path, post_type)
    if term is not None:
        q = q & Q(terms__term__slug=term)
        key_path = "{}_post_related-{}".format(key_path, term)
    if force or key_path not in cache:
        if order == "newest":
            posts = list(Post.objects.filter(q).order_by("-id").distinct().values_list('id', flat=True))
        else:
            if related is None:
                posts = list(Post.objects.filter(q).order_by("-measure__score").distinct().values_list('id', flat=True))
            else:
                posts = query_maker.query_related({"id": related, "limit": query.get("page_size", 6)})
        cache.set(key_path, posts, timeout=60 * 60 * 24)
    else:
        posts = cache.get(key_path)
    start = query.get("offset", 0)
    end = query.get("offset", 0) + query.get("page_size", 10)
    return {
        "results": list(map(lambda x: make_post(False, host_name, str(x), {
            "master": False,
            "user": query.get("user")
        }), posts[start: end])),
        "count": len(posts)
    }


def make_term_list(force, host_name, query):
    order = query.get("order")
    key_path = host_name + "_list_term" + order
    taxonomy = query.get("taxonomy")
    related = query.get("related")
    q = Q(publication__host=host_name)
    if query.get("publications"):
        q = q | Q(publication__id__in=query.get("publications"))
    show_cms = query.get("show_cms")
    if show_cms is not None:
        q = q & Q(show_cms=show_cms)
        key_path = "{}_cms-{}".format(key_path, show_cms)
    if taxonomy:
        key_path = "{}_taxonomy-{}".format(key_path, taxonomy)
        q = q & Q(taxonomy=taxonomy)
    if related:
        if query.get("reverse"):
            key_path = "{}_related__reverse-{}".format(key_path, related)
            q = q & Q(related_reverse__id=related)
        else:
            key_path = "{}_related-{}".format(key_path, related)
            q = q & Q(related__id=related)
    if query.get("search"):
        q = q & Q(term__title__icontains=query.get("search"))
    if (force or key_path not in cache) or query.get("search"):
        if order == "newest":
            terms = PublicationTerm.objects.filter(q).distinct().order_by("-id").values_list("id", flat=True)
        else:
            terms = PublicationTerm.objects.filter(q).distinct().order_by("-measure__score").values_list("id",
                                                                                                         flat=True)
        if not query.get("search"):
            cache.set(key_path, terms, timeout=60 * 60 * 24)
    else:
        terms = cache.get(key_path)
    start = query.get("offset", 0)
    end = query.get("offset", 0) + query.get("page_size", 10)
    return {
        "results": list(map(lambda x: make_term(False, x, False), terms[start: end])),
        "count": len(terms)
    }


def make_term(force, term_id, master=False):
    if term_id is None:
        return None
    key_path = "{}_{}".format("term", term_id)
    if force or key_path not in cache:
        term = dict(PubTermSerializer(PublicationTerm.objects.get(pk=term_id)).data)
        cache.set(key_path, term)
    else:
        term = cache.get(key_path)
    return term
