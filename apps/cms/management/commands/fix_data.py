from django.core.management.base import BaseCommand
from apps.cms.models import PublicationTerm


class Command(BaseCommand):
    def handle(self, *args, **options):
        tillandsia = PublicationTerm.objects.get(taxonomy="genus", term__slug="tillandsia")
        plants = tillandsia.posts.filter(post_type="plant")
        for plant in plants:
            plant.meta["soil"] = "Don't need"
            plant.save()
            print(plant)
