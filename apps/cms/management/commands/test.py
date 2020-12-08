from django.core.management.base import BaseCommand
from apps.cms.models import Post, Term, SearchKeyword, Publication, PublicationTerm
from utils.web_checker import get_keyword_suggestion
import requests
from django.contrib.auth.models import User
from utils.instagram import get_comment, fetch_avatar


class Command(BaseCommand):
    def handle(self, *args, **options):
        pt = PublicationTerm.objects.get(pk=13909)
        print(pt.entities())
