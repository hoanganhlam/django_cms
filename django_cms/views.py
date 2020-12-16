from django.http import HttpResponse
from django.template import loader
from apps.cms.models import Publication, PublicationTerm, Post


def sitemap_style(request):
    template = loader.get_template('./main-sitemap.xsl')
    return HttpResponse(template.render({}, request), content_type='text/xml')


def sitemap_index(request):
    sm = []
    template = loader.get_template('./sitemap_index.xml')
    if request.GET.get("host"):
        pub = Publication.objects.get(host=request.GET.get("host"))
        sm = sm + list(map(
            lambda x: "https://{0}/{1}-sitemap.xml".format(pub.host, x.get("label")),
            filter(lambda x: x.get("sitemap", False), pub.options.get("post_types"))
        ))
        sm = sm + list(map(
            lambda x: "https://{0}/{1}-sitemap.xml".format(pub.host, x.get("label")),
            filter(lambda x: x.get("sitemap", False), pub.options.get("taxonomies"))
        ))
    return HttpResponse(template.render({
        "sitemaps": sm
    }, request), content_type='text/xml')


def sitemap_detail(request, flag):
    ds = []
    template = loader.get_template('./sitemap.xml')
    if request.GET.get("host"):
        pub = Publication.objects.get(host=request.GET.get("host"))
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
                    lambda x: make_url(x, options, pub.host),
                    Post.objects.filter(
                        post_type=flag,
                        primary_publication=pub,
                        db_status=1,
                        status="POSTED"
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
    if "taxonomies" in options:
        setattr(instance, "location", location.format(slug=instance.slug, post_type=instance.post_type))
    else:
        setattr(instance, "location", location.format(slug=instance.term.slug, taxonomy=instance.taxonomy))
    return instance
