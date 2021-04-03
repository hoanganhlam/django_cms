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
        family = "Commelinaceae"
        url = "https://en.wikipedia.org/wiki/List_of_Commelinaceae_genera"
        selector = "#mw-content-text > div.mw-parser-output > table > tbody > tr"
        default_meta = {
            "soil": "mix",
            "light": "2",
            "humidity": "2",
            "toxicity": True,
            "watering": "2",
            "fertilizing": "2",
            "propagation": ["cuttings", "division", "storage_organs"],
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
            sub_family = None

            if len(elm.select("td")) > 0:
                title = elm.select("td")[0].select("i a")[0].find(text=True).title()
                sub_family = elm.select("td")[2].select("a")[0].find(text=True).title()
                if "/wiki/" in elm.select("td")[0].select("i a")[0].get("href"):
                    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + elm.select("td")[0].select("i a")[
                        0].get("href").replace("/wiki/", "")
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
                        taxonomy="genus",
                        defaults={
                            "description": description,
                            "meta": default_meta,
                            "show_cms": media_url is not None
                        }
                    )
                    if media_url and term_pub.media is None:
                        try:
                            term_pub.media = Media.objects.save_url(media_url)
                        except Exception as e:
                            print(e)
                    if term_pub.description is None:
                        term_pub.description = description
                    if term_pub.meta is None:
                        term_pub.meta = {}
                    if term_pub.meta.get("soil") is None:
                        term_pub.meta["soil"] = default_meta.get("soil")
                    if term_pub.meta.get("light") is None:
                        term_pub.meta["light"] = default_meta.get("light")
                    if term_pub.meta.get("humidity") is None:
                        term_pub.meta["humidity"] = default_meta.get("humidity")
                    if term_pub.meta.get("toxicity") is None:
                        term_pub.meta["toxicity"] = default_meta.get("toxicity")
                    if term_pub.meta.get("watering") is None:
                        term_pub.meta["watering"] = default_meta.get("watering")
                    if term_pub.meta.get("fertilizing") is None:
                        term_pub.meta["fertilizing"] = default_meta.get("fertilizing")
                    if term_pub.meta.get("propagation") is None:
                        term_pub.meta["propagation"] = default_meta.get("propagation")
                    if term_pub.meta.get("temperature") is None:
                        term_pub.meta["temperature"] = default_meta.get("temperature")

                    family_related = list(family_instance.related.all()) + [family_instance]
                    old_related = term_pub.related.all()
                    for related in family_related:
                        if related not in old_related:
                            term_pub.related.add(related)

                    if sub_family:
                        term_sub_family, is_created = Term.objects.get_or_create(slug=slugify(sub_family), defaults={
                            "title": sub_family
                        })
                        term_pub_sub_family, is_created = PublicationTerm.objects.get_or_create(
                            publication=pub,
                            term=term_sub_family,
                            taxonomy="family",
                            defaults={
                                "description": description,
                                "meta": default_meta,
                                "show_cms": media_url is not None
                            }
                        )
                        if term_pub_sub_family not in term_pub.related.all():
                            term_pub.related.add(term_pub_sub_family)
                    term_pub.save()
                print(title)
