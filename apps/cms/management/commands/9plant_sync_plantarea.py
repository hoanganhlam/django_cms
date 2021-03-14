from django.core.management.base import BaseCommand
from apps.cms.models import Post, Publication, PublicationTerm, Term
from utils.caching import make_post
from django.template.defaultfilters import slugify
import json
import random


class Command(BaseCommand):
    def handle(self, *args, **options):
        plant_nine = Publication.objects.get(pk=7)
        plant_area = Publication.objects.get(pk=16)
        stores = Post.objects.filter(primary_publication=plant_nine, post_type="store", meta__ig_username__isnull=False)\
            .prefetch_related("user", "user__profile")
        for store in stores:
            store.meta["ig"] = store.meta["ig_username"]
            store.save()
