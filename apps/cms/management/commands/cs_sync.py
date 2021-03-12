from django.core.management.base import BaseCommand
from apps.cms.models import Post, Publication, PublicationTerm, Term
from django.template.defaultfilters import slugify
import json
import random


class Command(BaseCommand):
    def handle(self, *args, **options):
        maker = Publication.objects.get(pk=3)
        sp = Publication.objects.get(pk=24)
        for term in sp.pub_terms.filter(taxonomy="tag"):
            print(term.title)
            term.taxonomy = "cheat-sheet"
            term.save()
