from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.repository.management.commands.fetcher import fetch_npm
from apps.repository.models import Repository


class Command(BaseCommand):
    def handle(self, *args, **options):
        q = ~Q(id_github=None) | Q(id_github='')
        q = q & Q(taxonomies__slug="vue-loader")
        queryset = Repository.objects.filter(q)
        for repo in queryset:
            fetch_npm(repo)
