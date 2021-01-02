from django.core.management.base import BaseCommand
from apps.media.models import Media


class Command(BaseCommand):
    def handle(self, *args, **options):
        medias = Media.objects.order_by("-id")
        for media in medias:
            media.path.name = media.path.name.replace("favdes/images/", "")
            media.save()
