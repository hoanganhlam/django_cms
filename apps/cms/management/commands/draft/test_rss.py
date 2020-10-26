from django.core.management.base import BaseCommand
import feedparser


class Command(BaseCommand):
    def handle(self, *args, **options):
        x = feedparser.parse("https://gen.medium.com/feed")
        print(x)
