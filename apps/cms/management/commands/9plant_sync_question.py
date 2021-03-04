from django.core.management.base import BaseCommand
from apps.cms.models import Post, Publication, PublicationTerm, Term
from django.template.defaultfilters import slugify
import json
import random


class Command(BaseCommand):
    def handle(self, *args, **options):
        nine = Publication.objects.get(pk=7)
        universe = Publication.objects.get(pk=15)
        plants = Post.objects.filter(primary_publication=nine, post_type="plant")
        for plant in plants:
            pass