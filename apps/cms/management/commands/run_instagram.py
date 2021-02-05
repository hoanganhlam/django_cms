from django.core.management.base import BaseCommand
from apps.cms.tasks import sync_plant_universe


class Command(BaseCommand):
    def handle(self, *args, **options):
        sync_plant_universe.apply_async()
