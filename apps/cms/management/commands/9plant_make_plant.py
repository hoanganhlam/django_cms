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


def sync_ig_user(user_raw):
    if user_raw is None:
        return None
    test_user, created = User.objects.get_or_create(username=user_raw.get("username"))
    user = test_user
    if created:
        raw_avatar = fetch_avatar(user_raw.get("profile_pic_id"))
        media = None
        if raw_avatar:
            media = Media.objects.save_url(raw_avatar)
            print(MediaSerializer(media).data.get("id"))
        test_profile, is_created = Profile.objects.get_or_create(
            user=user,
            defaults={
                "nick": user_raw.get("full_name"),
                "options": {"source": "instagram"},
                "media": media if media is not None else None
            }
        )
        if test_profile.media is None:
            if test_profile.media is None:
                test_profile.nick = user_raw.get("full_name")
                test_profile.options = {"source": "instagram"}
                test_profile.media = media if media is not None else None
                test_profile.save()
    return user


class Command(BaseCommand):
    def handle(self, *args, **options):
        admin = User.objects.get(pk=1)
        pub = Publication.objects.get(host="9plant.com")
        pub_15 = Publication.objects.get(pk=15)
        genus = PublicationTerm.objects.get(publication=pub, term__slug="peperomia", taxonomy="genus")
        species = PublicationTerm.objects.filter(publication=pub, related=genus, term__title__startswith="Peperomia")
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
                        show_cms=True,
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
                test.show_cms = True
                test.status = "POSTED"
                test.save()
                print(test.title)


