from django.core.management.base import BaseCommand
from apps.cms.models import Post, Term, SearchKeyword, Publication, PublicationTerm
from utils.web_checker import get_keyword_suggestion
import requests
from django.contrib.auth.models import User
from utils.instagram import get_comment, fetch_avatar
from apps.media.models import Media
from django.db.models import Count, Q


class Command(BaseCommand):
    def handle(self, *args, **options):
        q = ~Q(related__taxonomy="origin")
        tax_terms = PublicationTerm.objects.filter(
            publication__id=7,
            taxonomy="species",
            related__taxonomy__in=["genus", "origin"]
        )
        for term in tax_terms:
            for related in term.related.all():
                all_genus_related = related.related.all()
                for g_related in all_genus_related:
                    if g_related not in term.related.all():
                        term.related.add(g_related)
            if term.options is None:
                term.options = {}
            term.options["is_primary"] = True
            term.save()
