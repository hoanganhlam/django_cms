from django.core.management.base import BaseCommand
from apps.cms.models import Post, Publication, PublicationTerm
from utils import caching_v2


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('pub', type=int)

    def handle(self, *args, **kwargs):
        pub = Publication.objects.get(pk=kwargs["pub"])
        posts = pub.posts.order_by("-id").filter(show_cms=True)
        terms = pub.terms.order_by("-id").filter(show_cms=True)
        for item in posts:
            caching_v2.make_post(pub.host, {
                "instance": item.id
            }, True)
        for item in terms:
            caching_v2.make_term(pub.host, {
                "instance": item.id
            }, True)

