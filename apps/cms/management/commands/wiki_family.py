import json
import random
import re
import requests

from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString
from django.core.management.base import BaseCommand
from django.template.defaultfilters import slugify
from apps.cms.models import PublicationTerm, Publication, Post, Term
from apps.media.models import Media


def get_field(title, genera, data, f):
    if data.get(f) is not None and len(data.get(f)) > 1:
        return random.choice(data.get(f)).replace("{{title}}", title).replace("{{genera}}", genera)
    return None


def clean_origin(ori):
    return ori.replace(" – ", "").strip()


class Command(BaseCommand):
    def handle(self, *args, **options):
        family = "Bromeliaceae"
        url = "https://en.wikipedia.org/wiki/Bromeliaceae"
        selector = "#mw-content-text > div.mw-parser-output > div.div-col > ul"
        family_instance = PublicationTerm.objects.filter(term__slug=slugify(family), taxonomy="family").first()
        pub = Publication.objects.get(pk=7)
        r = requests.get(url)
        soup = BeautifulSoup(r.content, features="html.parser")
        elms = soup.select(selector)
        for elm in elms:
            lis = elm.select("li")
            for li in lis:
                title = li.find(text=True).title()
                media_url = None
                if li.find("a") and "/wiki/" in li.find("a").get("href"):
                    r2 = requests.get(
                        "https://en.wikipedia.org/api/rest_v1/page/summary/" + li.find("a").get("href").replace(
                            "/wiki/", ""))
                    r2_data = r2.json()
                    description = r2_data.get("extract")[:400]
                    if r2_data.get("originalimage"):
                        media_url = r2_data.get("originalimage").get("source")

                    term, is_created = Term.objects.get_or_create(slug=slugify(title), defaults={
                        "title": title
                    })
                    media = None
                    if media_url:
                        try:
                            media = Media.objects.save_url(media_url)
                        except Exception as e:
                            print(e)
                    term_pub, is_created = PublicationTerm.objects.get_or_create(
                        publication=pub,
                        term=term,
                        taxonomy="genus",
                        defaults={
                            "description": description,
                            "media": media,
                            "meta": {
                                "soil": "mix",
                                "light": "2",
                                "humidity": "3",
                                "toxicity": False,
                                "watering": "1",
                                "fertilizing": "1",
                                "propagation": ["cuttings", "division", "offsets"],
                                "temperature": "2"
                            },
                            "show_cms": True
                        }
                    )
                    family_related = list(family_instance.related.all()) + [family_instance]
                    old_related = term_pub.related.all()
                    for related in family_related:
                        if related not in old_related:
                            term_pub.related.add(related)
