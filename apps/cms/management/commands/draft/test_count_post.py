from django.core.management.base import BaseCommand
from apps.cms.models import Post
import feedparser


class Command(BaseCommand):
    def handle(self, *args, **options):
        results = Post.objects.filter(post_type="post", post_related__isnull=True, publications=7)
        plant = Post.objects.get(pk=9612)
        for re in results:
            re.post_related.add(plant)
        print(len(results))
