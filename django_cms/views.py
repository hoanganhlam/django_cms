from django.http import HttpResponse
from django.template import loader
from apps.cms.models import Publication, PublicationTerm, Post


def sitemap_style(request):
    template = loader.get_template('./main-sitemap.xsl')
    return HttpResponse(template.render({}, request), content_type='text/xml')


def sitemap_index(request):
    sm = []
    template = loader.get_template('./sitemap_index.xml')
    if request.GET.get("host") or request.headers.get("Host-Domain"):
        host_source = request.GET.get("host")
        host_domain = request.GET.get("host")
        if request.headers.get("Host-Domain"):
            host_domain = request.headers.get("Host-Domain")
            host_source = request.headers.get("Host-Domain")
        if request.GET.get("Source-Domain"):
            host_source = request.GET.get("Source-Domain")

        pub = Publication.objects.get(host=host_source)
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
        host_source = request.GET.get("host")
        if request.headers.get("Host-Domain"):
            host_domain = request.headers.get("Host-Domain")
            host_source = request.headers.get("Host-Domain")
        if request.GET.get("Source-Domain"):
            host_source = request.GET.get("Source-Domain")
        pub = Publication.objects.get(host=host_source)
        flat_taxonomies = list(map(lambda x: x.get("label"), pub.options.get("taxonomies")))
        flat_post_types = list(map(lambda x: x.get("label"), pub.options.get("post_types")))
        if flag in flat_taxonomies:
            options = pub.options.get("taxonomies")[flat_taxonomies.index(flag)]
            ds = list(
                map(
                    lambda x: make_url(x, options, pub.host),
                    PublicationTerm.objects.filter(
                        taxonomy=flag,
                        publication=pub,
                        db_status=1
                    ).prefetch_related("term")
                ))
        elif flag in flat_post_types:
            options = pub.options.get("post_types")[flat_post_types.index(flag)]
            ds = list(
                map(
                    lambda x: make_url(x, options, host_domain),
                    Post.objects.filter(
                        post_type=flag,
                        primary_publication=pub,
                        db_status=1,
                        status="POSTED",
                        show_cms=True
                    )))
    return HttpResponse(template.render({
        "dataset": ds
    }, request), content_type='text/xml')


def make_url(instance, options, hostname):
    if "taxonomies" in options:
        patterns = ['slug', 'post_type', 'id', 'pid']
        setattr(instance, "priority", 0.8)
    else:
        setattr(instance, "priority", 1)
        patterns = ['slug', 'taxonomy', 'id', 'pid']
    location = "https://" + hostname
    for elm in options.get("url_pattern"):
        if elm in patterns:
            location = location + "{" + elm + "}"
        else:
            location = location + elm
    if type(instance) == Post:
        setattr(instance, "location", location.format(slug=instance.slug, post_type=instance.post_type, id=instance.id))
    else:
        setattr(instance, "location", location.format(slug=instance.term.slug, taxonomy=instance.taxonomy, id=instance.id))
    return instance
