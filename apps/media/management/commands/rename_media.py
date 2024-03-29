from django.core.management.base import BaseCommand
from apps.media.models import Media
from apps.media.api.serializers import MediaSerializer


class Command(BaseCommand):
    def handle(self, *args, **options):
        medias = Media.objects.order_by("-id")
        for media in medias:
            print(media.id)
            media.path.name = media.path.name.replace("favdes/images", "")
            media.save()
