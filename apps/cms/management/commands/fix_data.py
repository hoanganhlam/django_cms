from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.cms.models import Post
from apps.media.models import Media
from apps.media.api.serializers import MediaSerializer


class Command(BaseCommand):
    def handle(self, *args, **options):
        posts = Post.objects.filter(publications__id=5)
        for p in posts:
            if p.status == 'DRAFT':
                p.status = "POSTED"
                p.save()
            if p.options.get("medias"):
                medias = Media.objects.filter(id__in=p.options.get("medias"))
                print(MediaSerializer(medias, many=True).data)
