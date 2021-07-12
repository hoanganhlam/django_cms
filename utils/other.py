from rest_framework.utils.serializer_helpers import ReturnDict, ReturnList
from collections import OrderedDict
from apps.cms.models import Publication

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def check_inner(array, array2):
    for i in array:
        if i in array2:
            return True
    return False


def get_paginator(request):
    search = request.GET.get('search')
    page_size = 10 if request.GET.get('page_size') is None else int(request.GET.get('page_size'))
    page = 1 if request.GET.get('page') is None else int(request.GET.get('page'))
    offs3t = page_size * page - page_size,
    return {
        "search": search,
        "page_size": page_size,
        "page": page,
        "offs3t": offs3t,
        "order": request.GET.get('order')
    }


def clone_dict(dct, schemas, out=None):
    if type(dct) == OrderedDict:
        dct = dict(dct)
    if out is None:
        if type(dct) == dict or type(dct) == ReturnDict:
            out = {}
        if type(dct) == list:
            out = []
    if type(dct) == dict or type(dct) == ReturnDict:
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


def make_static_fields(options, pub_id):
    static_fields = []
    for item in options["post_types"]:
        static_fields.append(item["label"])
        if item.get("sitemap"):
            for pt in ["url_pattern_list", "url_pattern"]:
                if item.get(pt):
                    for x in item[pt]:
                        if x != "/" and "__" not in x:
                            static_fields.append(x)
    pub = Publication.objects.get(pk=pub_id)
    pub.options["static_fields"] = static_fields
    pub.save()
    return static_fields
