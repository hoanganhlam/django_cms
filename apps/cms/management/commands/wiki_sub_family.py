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
        family = "Araceae"
        url = "https://en.wikipedia.org/wiki/List_of_Araceae_genera"
        selector = "#mw-content-text > div.mw-parser-output > table > tbody > tr"
        default_meta = {
            "soil": "mix",
            "light": "2",
            "humidity": "2",
            "toxicity": True,
            "watering": "2",
            "fertilizing": "2",
            "propagation": ["cuttings", "division", "offsets"],
            "temperature": "2"
        }

        family_instance = PublicationTerm.objects.filter(term__slug=slugify(family), taxonomy="family").first()
        pub = Publication.objects.get(pk=7)
        r = requests.get(url)
        soup = BeautifulSoup(r.content, features="html.parser")
        elms = soup.select(selector)
        for elm in elms:
            # title = elm.find(text=True).title()
            title = None
            url = None

            if len(elm.select("td")) > 0:
                title = elm.select("td")[2].select("a")[0].find(text=True).title()
                if "/wiki/" in elm.select("td")[2].select("a")[0].get("href"):
                    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + elm.select("td")[2].select("a")[0].get("href").replace("/wiki/", "")
            print(title)
            print(url)
            if title and url:
                media_url = None
                if elm.find("a") and "/wiki/" in elm.find("a").get("href"):
                    r2 = requests.get(url)
                    r2_data = r2.json()
                    description = r2_data.get("extract")[:400]
                    if r2_data.get("originalimage"):
                        media_url = r2_data.get("originalimage").get("source")
                    term, is_created = Term.objects.get_or_create(slug=slugify(title), defaults={
                        "title": title
                    })
                    term_pub, is_created = PublicationTerm.objects.get_or_create(
                        publication=pub,
                        term=term,
                        taxonomy="family",
                        defaults={
                            "show_cms": media_url is not None
                        }
                    )
                    if media_url and term_pub.media is None:
                        try:
                            term_pub.media = Media.objects.save_url(media_url)
                        except Exception as e:
                            print(e)
                    term_pub.description = description
                    term_pub.meta = default_meta

                    family_related = list(family_instance.related.all()) + [family_instance]
                    old_related = term_pub.related.all()
                    for related in family_related:
                        if related not in old_related:
                            term_pub.related.add(related)
                    term_pub.save()
