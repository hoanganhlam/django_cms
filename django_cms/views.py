from django.http import HttpResponse
from django.template import loader
from apps.cms.models import Publication, PublicationTerm, Post
from django.core.cache import cache
from utils.filter_query import query_boolean


def sitemap_style(request):
    template = loader.get_template('./main-sitemap.xsl')
    return HttpResponse(template.render({}, request), content_type='text/xml')


def sitemap_index(request):
    sm = []
    template = loader.get_template('./sitemap_index.xml')
    if request.GET.get("host") or request.headers.get("Host-Domain"):
        host_domain = request.GET.get("host")
        if request.headers.get("Host-Domain"):
            host_domain = request.headers.get("Host-Domain")
        pub = Publication.objects.get(host=host_domain)
        sm = sm + list(map(
            lambda x: "https://{0}/{1}-sitemap.xml".format(host_domain, x.get("label")),
            filter(lambda x: x.get("sitemap", False), pub.options.get("post_types"))
        ))
        sm = sm + list(map(
            lambda x: "https://{0}/{1}-sitemap.xml".format(host_domain, x.get("label")),
            filter(lambda x: x.get("sitemap", False), pub.options.get("taxonomies"))
        ))
    return HttpResponse(template.render({
        "sitemaps": sm
    }, request), content_type='text/xml')


def sitemap_detail(request, flag):
    ds = []
    template = loader.get_template('./sitemap.xml')
    if request.GET.get("host") or request.headers.get("Host-Domain"):
        host_domain = request.GET.get("host")
        if request.headers.get("Host-Domain"):
            host_domain = request.headers.get("Host-Domain")
        if request.headers.get("Source-Domain"):
            host_source = request.headers.get("Source-Domain")
        else:
            host_source = host_domain
        pub = Publication.objects.get(host=host_domain)
        flat_taxonomies = list(map(lambda x: x.get("label"), pub.options.get("taxonomies")))
        flat_post_types = list(map(lambda x: x.get("label"), pub.options.get("post_types")))

        if flag in flat_taxonomies:
            options = pub.options.get("taxonomies")[flat_taxonomies.index(flag)]
        elif flag in flat_post_types:
            options = pub.options.get("post_types")[flat_post_types.index(flag)]
        else:
            options = None
        ds = caching_sitemap(
            options, flat_taxonomies, flat_post_types, host_source, host_domain,
            query_boolean(request.GET.get("force")))
    return HttpResponse(template.render({
        "dataset": ds
    }, request), content_type='text/xml')


def caching_sitemap(options, taxonomies, post_types, host_source, host_domain, force=False):
    if options is None:
        return []
    key_path = "site_map_{host_domain}_{label}".format(host_domain=host_domain, label=options.get("label"))
    if key_path not in cache or force:
        print("A")
        items = []
        if options.get("label") in taxonomies:
            items = PublicationTerm.objects.filter(
                publication__host=host_source,
                taxonomy=options.get("label"),
                show_cms=True
            )
        elif options.get("label") in post_types:
            items = Post.objects.filter(
                primary_publication__host=host_source,
                post_type=options.get("label"),
                show_cms=True,
                db_status=1,
                status="POSTED",
            )
        cache.set(key_path, list(
            map(
                lambda x: x.url("https://" + host_domain, options.get("url_pattern"), taxonomies, post_types),
                items
            )
        ), timeout=60 * 60 * 24)
    return cache.get(key_path)
