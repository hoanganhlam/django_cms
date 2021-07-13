from django.core.cache import cache
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from utils.other import clone_dict
from utils import caching_v3, filter_query
from utils import schemas as default_schemas
from apps.cms import models as cms_models
from django.contrib.auth.models import User

CACHE_TTL = getattr(settings, 'CACHE_TTL')


def test_mapping(params, patterns):
    result = True
    i = 0
    for param in params:
        if not (param == patterns[i] or "__" in patterns[i]):
            result = False
            break
        i = i + 1
    return result


def retouch_model_field(params, model_fields, model_name, check_pattern):
    count = len(params)
    out = None
    if not model_fields:
        return out
    for field in model_fields:
        if field.get("sitemap"):
            if field.get(check_pattern):
                field["total_params"] = (len(field.get(check_pattern)) // 2)
                if field["total_params"] == count:
                    field["model_name"] = model_name
                    field["is_list"] = "list" in check_pattern
                    field["pattern_params"] = list(filter(lambda x: x != "/", field.get(check_pattern)))
                    if test_mapping(params, field["pattern_params"]):
                        out = field
                        break
    return out


def get_path_info(publication, path):
    title = publication["title"]
    description = publication["description"]
    path_pattern = None
    tp = "home"
    taxonomy = "category"
    post_type = "post"
    value = {}
    addon_fields = []
    related_fields = []
    taxonomy_fields = []
    options = publication.get("options") or {
        "post_types": [],
        "taxonomies": [],
        "theme": {}
    }
    user_page = "profile"
    if options.get("theme") and options["theme"].get("general") and options["theme"]["general"].get(
            "define_member_page"):
        user_page = options["theme"]["general"]["define_member_page"]
    if options.get("default_post_type"):
        post_type = options.get("default_post_type")
    if options.get("default_taxonomy"):
        taxonomy = options["default_taxonomy"]
    params = list(filter(lambda x: x != "", path.split("/")))
    count = len(params)
    if count > 0:
        if params[0] == user_page:
            tp = "user"
            if count == 2:
                value["user"] = params[1]
        else:
            check = retouch_model_field(params, options["post_types"], "post", "url_pattern_list")
            if not check:
                check = retouch_model_field(params, options["taxonomies"], "term", "url_pattern_list")
            if not check:
                check = retouch_model_field(params, options["post_types"], "post", "url_pattern")
            if not check:
                check = retouch_model_field(params, options["taxonomies"], "term", "url_pattern")
            if check:
                related_fields = check.get("related", [])
                taxonomy_fields = check.get("taxonomies", [])
                addon_fields = check.get("field_addons", [])
                path_pattern = "/".join(check["pattern_params"])
                tp = check["model_name"]
                if tp == "post":
                    post_type = check["label"]
                else:
                    taxonomy = check["label"]
                if check.get("is_list"):
                    tp = "{}_list".format(tp)
                i = 0
                for p in check["pattern_params"]:
                    if "__" in p:
                        value[p] = params[i]
                    i = i + 1
            else:
                tp = "404"
    return {
        "path": path_pattern,
        "title": title,
        "description": description,
        "type": tp,  # home | post | term | post_list | term_list | user | 404
        "taxonomy": taxonomy,
        "post_type": post_type,
        "value": value,
        "addon_fields": addon_fields,
        "related_fields": related_fields,
        "taxonomy_fields": taxonomy_fields
    }


def path_to_data(publication, request):
    options = publication.get("options") or {}
    # THEME OPTION
    theme_options = options.get("theme") or {
        "general": {},
        "homepage": {},
        "term": {},
        "post": {},
        "user": {}
    }
    if not theme_options.get("general"):
        theme_options["general"] = {}
    if not theme_options.get("homepage"):
        theme_options["homepage"] = {}
    if not theme_options.get("term"):
        theme_options["term"] = {}
    if not theme_options.get("post"):
        theme_options["post"] = {}
    if not theme_options.get("user"):
        theme_options["user"] = {}
    # INITIAL
    host_name = publication["host"]
    path = request.GET["path"]
    is_force = filter_query.query_boolean(request.GET.get("force"), False)
    default_order = theme_options["general"].get("default_order", "p")
    order = request.GET.get("order", default_order)
    page = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", theme_options["general"].get("limit", 10))
    info = get_path_info(publication, path)
    query = {
        "term": None,
        "related": None,
        "order": order,
        "page": page,
        "page_size": page_size,
        "taxonomy": info["taxonomy"],
        "post_type": info["post_type"],
        "value": None,
        "user": None
    }
    data = {}
    username = info["value"].get("user")
    if not username and request.user.is_authenticated:
        username = request.user.username
    # FETCH VALUE
    for key in info["value"].keys():
        if key.startswith(info["taxonomy"]):
            if type(info["value"][key]) is int or info["value"][key].isnumeric():
                pk = info["value"][key]
            else:
                kp = "{}__{}__{}".format(host_name, info["taxonomy"], info["value"][key])
                if kp not in cache:
                    pk = cms_models.PublicationTerm.objects.get(
                        publication_id=publication["id"],
                        taxonomy=info["taxonomy"],
                        term__slug=info["value"][key]
                    ).id
                    cache.set(kp, pk, CACHE_TTL * 12)
                else:
                    pk = cache.get(kp)
            if info["type"] == "term":
                query["term"] = pk
            data[info["taxonomy"]] = caching_v3.make_term(
                host_name,
                pk,
                theme_options["term"].get("{}_schemas".format(info["taxonomy"]), default_schemas.TERM_DETAIL),
                is_force
            )
            info["title"] = data[info["taxonomy"]]["term"]["title"]
            info["description"] = data[info["taxonomy"]]["description"]
            if data[info["taxonomy"]].get("meta"):
                if data[info["taxonomy"]]["meta"].get("seo_title"):
                    info["title"] = data[info["taxonomy"]]["meta"]["seo_title"]
                if data[info["taxonomy"]]["meta"].get("seo_description"):
                    info["description"] = data[info["taxonomy"]]["meta"]["seo_description"]
        elif key.startswith(info["post_type"]):
            if type(info["value"][key]) is int or info["value"][key].isnumeric():
                pk = info["value"][key]
            else:
                kp = "{}__{}__{}".format(host_name, info["post_type"], info["value"][key])
                if kp not in cache or is_force:
                    pk = cms_models.Post.objects.get(slug=info["value"][key]).id
                    cache.set(kp, pk, CACHE_TTL * 12)
                else:
                    pk = cache.get(kp)
            data[info["post_type"]] = caching_v3.make_post(
                host_name,
                pk,
                theme_options["post"].get("{}_schemas".format(info["post_type"]), default_schemas.POST_DETAIL),
                is_force
            )
            if info["type"] == "post":
                info["title"] = data[info["post_type"]]["title"]
                info["description"] = data[info["post_type"]]["description"]
                if data[info["post_type"]].get("meta"):
                    if data[info["post_type"]]["meta"].get("seo_title"):
                        info["title"] = data[info["post_type"]]["meta"]["seo_title"]
                    if data[info["post_type"]]["meta"].get("seo_description"):
                        info["description"] = data[info["post_type"]]["meta"]["seo_description"]
                default_limit = theme_options["general"].get("limit_list_related", 5)
                if theme_options["post"].get("{}_related_post_types".format(info["post_type"])):
                    info["related_fields"] = theme_options["post"]["{}_related_post_types".format(info["post_type"])]
                if theme_options["post"].get("{}_taxonomies".format(info["post_type"])):
                    info["taxonomy_fields"] = theme_options["post"]["{}_taxonomies".format(info["post_type"])]
                for pt in info["related_fields"]:
                    q = {
                        "term": None,
                        "page_size": theme_options["post"].get("{}_limit".format(pt), default_limit),
                        "order": theme_options["post"].get("{}_order".format(pt), default_order),
                        "page": 1,
                        "post_type": pt,
                        "related": pk,
                        "taxonomy": None,
                        "value": None,
                        "user": None
                    }
                    data[info["post_type"]][pt] = caching_v3.make_list_post(
                        host_name,
                        q,
                        theme_options["post"].get("{}_schemas_list".format(pt), default_schemas.POST_LIST),
                        is_force
                    )
        elif key == "user" and username:
            kp = "user__{}".format(username)
            if kp not in cache or is_force:
                pk = User.objects.get(username=username).id
                cache.set(kp, pk, CACHE_TTL * 12)
            else:
                pk = cache.get(kp)
            data["user"] = caching_v3.make_user(
                pk,
                theme_options["user"].get("user_schemas", default_schemas.USER_DETAIL),
                is_force
            )
            info["title"] = data["user"]["username"]
            if data["user"].get("profile"):
                if data["user"]["profile"].get("full_name"):
                    info["title"] = data["user"]["profile"]["full_name"]
                if data["user"]["profile"].get("bio"):
                    info["description"] = data["user"]["profile"]["bio"]
            query["user"] = pk
    # FETCH LIST
    if info["type"] == "home":
        data_sources = theme_options["homepage"].get("data_sources") or ["post"]
    elif info["type"] == "user":
        data_sources = theme_options["user"].get("data_sources") or ["post"]
    elif info["type"] in ["term", "post_list"]:
        data_sources = ["post"]
    elif info["type"] == "term_list":
        data_sources = ["term"]
    else:
        data_sources = []
    # FETCH DATA LIST
    for source in data_sources:
        if source == "post":
            data["response_post"] = caching_v3.make_list_post(
                host_name,
                query,
                theme_options["post"].get("{}_schemas_list".format(info["post_type"]), default_schemas.POST_LIST),
                is_force
            )
        elif source == "term":
            data["response_term"] = caching_v3.make_list_term(
                host_name,
                query,
                theme_options["term"].get("{}_schemas_list".format(info["taxonomy"]), default_schemas.TERM_LIST),
                is_force
            )
    return {
        "i": info,
        "d": data
    }


# ==========================================================================
@api_view(['GET', 'POST'])
def view_cache(request, host_name):
    path = request.GET.get("path")
    if path:
        is_force = filter_query.query_boolean(request.GET.get("force"), False)
        is_server = filter_query.query_boolean(request.GET.get("is_server"), False)
        publication = caching_v3.make_pub(hostname=host_name, force=is_force)
        user = caching_v3.make_user(
            request.user,
            default_schemas.USER_DETAIL,
            False
        ) if request.user.is_authenticated else None
        key_path = "{}__{}".format(host_name, path)
        if key_path not in cache or is_force:
            out = path_to_data(publication, request)
            cache.set(key_path, out, timeout=CACHE_TTL * 12)
        else:
            out = cache.get(key_path)
        if is_server:
            if publication["options"].get("theme") and publication["options"]["theme"].get("general"):
                for field in publication["options"]["theme"]["general"].get("filter_fields", []):
                    publication[field] = caching_v3.make_list_term(
                        publication["host"],
                        {
                            "page_size": 5,
                            "page": 1,
                            "order": "p",
                            "related": None,
                            "taxonomy": field
                        },
                        default_schemas.TERM_LIST,
                        is_force
                    )
        return Response({
            "i": out.get("i"),  # INFO
            "d": out.get("d"),  # DATA
            "p": publication if is_server else None,  # PUB
            "u": user  # USER
        })
