from django.core.management.base import BaseCommand
from apps.cms.models import Post, Publication, PublicationTerm, Term
from django.template.defaultfilters import slugify
import json
import random
import requests


class Command(BaseCommand):
    def handle(self, *args, **options):
        pub = Publication.objects.get(pk=24)
        for term in pub.pub_terms.filter(taxonomy="cheat-sheet", show_cms=True, meta__isnull=False).prefetch_related("term"):
            seo_title = "{} {}".format(term.term.title.title(), "Cheat Sheet")\
                .replace("Cheat Sheet Cheat Sheet", "Cheat Sheet")\
                .replace("Cheatsheet Cheat Sheet", "Cheat Sheet")
            term.meta["seo_title"] = seo_title
            term.save()
