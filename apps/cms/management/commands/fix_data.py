from django.core.management.base import BaseCommand
from apps.cms.models import Post, Term, SearchKeyword, Publication, PublicationTerm
from utils.web_checker import get_keyword_suggestion
import requests
from django.contrib.auth.models import User
from utils.instagram import get_comment, fetch_avatar
from apps.media.models import Media


class Command(BaseCommand):
    def handle(self, *args, **options):
        tax_terms = PublicationTerm.objects.filter(publication__id=7, taxonomy="species", term__title__startswith="/java/")
        print(tax_terms.count())
        for term in tax_terms:
            print(term.id)
            term.delete()
