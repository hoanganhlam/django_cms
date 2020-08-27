from django.core.management.base import BaseCommand
from apps.cms.models import Post


class Command(BaseCommand):
    def handle(self, *args, **options):
        posts = Post.objects.all()
        for post in posts:
            if post.options and post.meta and post.meta.get("media") is None:
                post.meta['media'] = post.options.get("media")
                post.save()
                print(post.id)
