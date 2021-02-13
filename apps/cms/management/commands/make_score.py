from django.core.management.base import BaseCommand
from apps.cms.models import PublicationTerm


class Command(BaseCommand):
    def handle(self, *args, **options):
        items = PublicationTerm.objects.all()
        for item in items:
            if item.measure is None:
                item.measure = {}
            # total view 1
            # total vote 1
            # total posts 1
            item.measure["score"] = item.posts.count()
            item.save()
