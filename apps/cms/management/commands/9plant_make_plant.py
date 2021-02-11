from django.core.management.base import BaseCommand
from apps.cms.models import Post, Term, SearchKeyword, Publication, PublicationTerm
from utils.web_checker import get_keyword_suggestion
import requests
from django.contrib.auth.models import User
from utils.instagram import get_comment, fetch_avatar
from django.template.defaultfilters import slugify
import json
import random
from utils.instagram import fetch_by_hash_tag
from apps.media.models import Media
from apps.media.api.serializers import MediaSerializer
from apps.authentication.models import Profile


def get_field(title, genera, data, f):
    if data.get(f) is not None:
        return random.choice(data.get(f)).replace("{{title}}", title).replace("{{genera}}", genera)
    return None


class Command(BaseCommand):
    def handle(self, *args, **options):
        posts = Post.objects.filter(title__startswith="Peperomia", description__isnull=True)
        for post in posts:
            post.show_cms = False
            post.save()
        return

        genera_name = "spathiphyllum"
        pub = Publication.objects.get(host="9plant.com")
        genus = PublicationTerm.objects.get(publication=pub, term__slug=genera_name, taxonomy="genus")
        species = PublicationTerm.objects.filter(publication=pub, related=genus, term__title__startswith=genera_name.capitalize())
        with open('genera_export.json') as json_file:
            data = json.load(json_file)
            for sp in species:
                test = Post.objects.filter(slug=sp.term.slug, post_type="plant", primary_publication=pub).first()
                if test is None:
                    test = Post.objects.create(
                        title=sp.term.title,
                        post_type="plant",
                        primary_publication=pub,
                        status="POSTED",
                        meta={
                            "score_temperature": int(genus.meta.get("temperature")),
                            "score_light": int(genus.meta.get("light")),
                            "score_watering": int(genus.meta.get("watering")),
                            "score_soil": genus.meta.get("soil"),
                            "score_humidity": int(genus.meta.get("humidity")),
                            "toxicity": genus.meta.get("toxicity"),
                            "score_fertilizing": int(genus.meta.get("fertilizing")),
                            "score_propagation": genus.meta.get("propagation"),

                            "temperature": get_field(sp.term.title, genus.term.title, data, "temperature"),
                            "light": get_field(sp.term.title, genus.term.title, data, "light"),
                            "watering": get_field(sp.term.title, genus.term.title, data, "watering"),
                            "soil": get_field(sp.term.title, genus.term.title, data, "soil"),
                            "humidity": get_field(sp.term.title, genus.term.title, data, "humidity"),
                            "fertilizing": get_field(sp.term.title, genus.term.title, data, "fertilizer"),

                            "propagation": get_field(sp.term.title, genus.term.title, data, "propagation"),
                            "re-potting": get_field(sp.term.title, genus.term.title, data, "re-potting"),
                        },
                        options={}
                    )
                    for related in sp.related.all():
                        test.terms.add(related)
                test.status = "POSTED"
                test.save()
                print(test.title)


