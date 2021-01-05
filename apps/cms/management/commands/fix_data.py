from django.core.management.base import BaseCommand
from apps.cms.models import Post, Term, SearchKeyword, Publication
from utils.web_checker import get_keyword_suggestion
import requests
from django.contrib.auth.models import User
from utils.instagram import get_comment, fetch_avatar
from apps.media.models import Media


class Command(BaseCommand):
    def handle(self, *args, **options):
        medias = Media.objects.filter(path__istartswith="guess").order_by("-id")
        print(medias.count())
        for media in medias:
            media.path.name = "/" + media.path.name
            media.save()
            print(media.id)
