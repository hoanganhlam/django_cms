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
        stores = Post.objects.filter(primary_publication=plant_nine, post_type="store")\
            .prefetch_related("user", "user__profile")
        for store in stores:
            if store.user.profile.nick and store.user.profile.options.get("source") == "instagram":
                store.meta["ig_username"] = store.title
                store.title = store.user.profile.nick
                store.save()
                make_post(Term, "9plant.com", store.id, {})
