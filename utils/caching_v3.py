from django.db.models import Q
from django.core.cache import cache
from django.conf import settings
from utils.other import clone_dict
from apps.cms.models import Post, PublicationTerm
from utils import query as query_maker
from utils import schemas as default_schemas

CACHE_TTL = getattr(settings, 'CACHE_TTL')


def flat_schema(schema):
    if type(schema) is dict:
        return (list(schema.keys()))[0]
    return schema


def make_pub(hostname, force):
    ch_key = "{}".format(hostname)
    if force or ch_key not in cache:
        data = query_maker.query_publication(hostname)
        cache.set(ch_key, data, timeout=CACHE_TTL * 12)
    else:
        data = cache.get(ch_key)
    return data


def get_url_pattern(host_name, model, item):
    label = item[model]
    pub = make_pub(host_name, False)
    if pub.get("options") and pub.get("options").get("{}_list".format(model)):
        scm = pub.get("options").get("{}_list".format(model)).get(label)
        if item.get("options") and item.get("options").get("primary_term"):
            term = make_term(host_name, item["options"]["primary_term"], default_schemas.TERM_DETAIL, False)
            item[term["taxonomy"]] = term
        if scm and scm.get("sitemap") and scm.get("url_pattern"):
            out = ""
            for ptn in scm.get("url_pattern"):
                if "__" in ptn:
                    arr = ptn.split("__")
                    tvl = item
                    for a in arr:
                        if a == label:
                            continue
                        if tvl is None:
                            break
                        tvl = tvl.get(a)
                    if tvl:
                        out = out + tvl
                    else:
                        out = out + "__"
                else:
                    out = out + ptn
            return out
    return None


def make_post(hostname, pk, schemas, force):
    ch_key = "{}__post_{}".format(hostname, pk)
    if force or ch_key not in cache:
        data = query_maker.query_post_detail(pk)
        data["to"] = get_url_pattern(hostname, "post_type", data)
        cache.set(ch_key, data, timeout=CACHE_TTL * 12)
    else:
        data = cache.get(ch_key)
    out_data = clone_dict(data, schemas, None)
    flat_schemas = list(map(lambda x: flat_schema(x), schemas))
    if "user" in flat_schemas and data.get("user_id"):
        x_schemas = schemas[flat_schemas.index("user")]
        if type(x_schemas) is str:
            x_schemas = default_schemas.USER_DETAIL
        else:
            x_schemas = x_schemas["user"]
        out_data["user"] = make_user(data.get("user_id"), x_schemas, False)
    if "terms" in flat_schemas and data.get("terms"):
        terms_schemas = schemas[flat_schemas.index("terms")]
        if type(terms_schemas) is str:
            terms_schemas = default_schemas.TERM_LIST
        else:
            terms_schemas = terms_schemas["terms"]
        out_data["terms"] = list(
            map(
                lambda x: make_term(hostname, x, terms_schemas, False),
                data["terms"]
            )
        )
    if "related" in flat_schemas and data.get("related"):
        x_schemas = schemas[flat_schemas.index("related")]
        if type(x_schemas) is str:
            x_schemas = default_schemas.POST_LIST
        else:
            x_schemas = x_schemas["related"]
        out_data["related"] = list(
            map(
                lambda x: make_post(hostname, x, x_schemas, False),
                data["related"]
            )
        )
    return out_data


def make_term(hostname, pk, schemas, force):
    ch_key = "{}__term_{}".format(hostname, pk)
    if force or ch_key not in cache:
        data = query_maker.query_term(pk)
        data["to"] = get_url_pattern(hostname, "taxonomy", data)
        cache.set(ch_key, data, timeout=CACHE_TTL * 12)
    else:
        data = cache.get(ch_key)
    return clone_dict(data, schemas, None)


def make_user(pk, schemas, force):
    ch_key = "term__{}".format(pk)
    if force or ch_key not in cache:
        data = query_maker.query_user(pk, {})
        cache.set(ch_key, data, timeout=CACHE_TTL * 12)
    else:
        data = cache.get(ch_key)
    return clone_dict(data, schemas, None)


def make_list_post(hostname, query, schemas, force):
    post_type = query["post_type"]
    term = query["term"]
    related = query["related"]
    order = query["order"]
    user = query["user"]
    ch_key = hostname
    if user:
        ch_key = "{}__user_{}".format(ch_key, user)
    if term:
        ch_key = "{}__term_{}".format(ch_key, term)
    if related:
        ch_key = "{}__related_{}".format(ch_key, related)
    ch_key = "{}__post_type_{}__order_{}".format(ch_key, post_type, order)
    if ch_key not in cache or force:
        q = Q(show_cms=True, post_type=post_type)
        if term is None and related is None:
            q = q & Q(primary_publication__host=hostname)
        if term is not None:
            q = q & Q(terms__id=term)
        if user:
            q = q & Q(user_id=user)
        if related is not None:
            q = q & (Q(post_related__id=related) | Q(post_related_revert__id=related))
        data = list(Post.objects.prefetch_related("term", "post_related").filter(q).values_list("id", flat=True))
    else:
        data = cache.get(ch_key)
    page_size = query["page_size"]
    page = query["page"]
    offset = page_size * page - page_size
    return {
        "results": list(map(lambda x: make_post(hostname, x, schemas, False), data[offset: offset + page_size])),
        "count": len(data)
    }


def make_list_term(hostname, query, schemas, force):
    taxonomy = query["taxonomy"]
    order = query["order"]
    related = query["related"]
    ch_key = hostname
    if related:
        ch_key = "{}__related_{}".format(ch_key, related)
    ch_key = "{}__taxonomy_{}__order_".format(ch_key, taxonomy, order)
    if ch_key not in cache or force:
        q = Q(show_cms=True, taxonomy=taxonomy)
        if related is None:
            q = q & Q(publication__host=hostname)
        else:
            q = q & (Q(related__id=related) | Q(related_revert__id=related))
        data = PublicationTerm.objects.prefetch_related("related").values_list("id", flat=True).filter(q)
    else:
        data = cache.get(ch_key)
    page_size = query["page_size"]
    page = query["page"]
    offset = page_size * page - page_size
    return {
        "results": list(map(lambda x: make_term(hostname, x, schemas, False), data[offset: offset + page_size])),
        "count": len(data)
    }
