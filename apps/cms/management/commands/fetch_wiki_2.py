import json
import random
import re
import requests

from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString
from django.core.management.base import BaseCommand
from django.template.defaultfilters import slugify
from apps.cms.models import PublicationTerm, Publication, Post


def get_field(title, genera, data, f):
    if data.get(f) is not None and len(data.get(f)) > 1:
        return random.choice(data.get(f)).replace("{{title}}", title).replace("{{genera}}", genera)
    return None


class Command(BaseCommand):
    def handle(self, *args, **options):
        genera = "Epipremnum"
        family = "Araceae"
        url = "https://en.wikipedia.org/wiki/Epipremnum"
        selector = "#mw-content-text > div.mw-parser-output > ol"

        pub = Publication.objects.get(pk=7)
        genus_instance = PublicationTerm.objects.filter(term__title=genera).first()
        r = requests.get(url)
        soup = BeautifulSoup(r.content, features="html.parser")
        elms = soup.select(selector)
        for elm in elms:
            lis = elm.select("li")
            for li in lis:
                title = li.find(text=True).title()
                if title == genera or title == "Subsp. " or title == "Var. ":
                    continue
                origins = []
                authors = []
                if len(li.contents) > 3:
                    for content in li.contents[3:]:
                        if type(content) is Tag and content.name not in ["sup", "ul"]:
                            origins = origins + content.find_all(text=True)
                        elif type(content) is NavigableString and content not in [" - ", ", ", " (", ")"]:
                            # if re.search(r'\((.*?)\)', content):
                            #     origins = origins + re.search(r'\((.*?)\)', content).group(1).split(",")
                            origins = origins + content.replace(" - ", "").split(",")
                if li.find("small") is not None:
                    authors.append(str(li.find("small").find(text=True)).strip())

                description_patterns = [
                    "{title} is a species of flowering plant in the {genera} family {family}",
                    "{title} is a species of {genera}",
                    "{title} is a perennial species in the genus {genera}, belonging to the family {family}",
                    "{title} is a plant in the family {family}",
                    "{title} is a flowering plant",
                ]

                origin_patterns = [
                    "found in {origin}",
                    "can be found in {origin}",
                    "native to {origin}"
                ]

                author_patterns = [
                    "was first scientifically described by {author}"
                ]

                ds = [random.choice(description_patterns)]
                if len(authors):
                    ds.append(random.choice(author_patterns))
                if len(origins):
                    ds.append(random.choice(origin_patterns))
                random.shuffle(ds)
                ds[0] = ds[0].capitalize()
                description = ", ".join(ds).format(
                    title=title,
                    plant=title,
                    origin=", ".join(origins) if len(origins) else None,
                    author=", ".join(authors) if len(authors) else None,
                    family=family,
                    genera=genera) + "."
                test = Post.objects.filter(slug__startswith=slugify(title), post_type="plant",
                                           primary_publication=pub).first()
                if test is None:
                    with open('genera_export.json') as json_file:
                        data = json.load(json_file)
                    test = Post.objects.create(
                        title=title,
                        description=description,
                        post_type="plant",
                        primary_publication=pub,
                        status="POSTED",
                        meta={
                            "score_temperature": int(genus_instance.meta.get("temperature")),
                            "score_light": int(genus_instance.meta.get("light")),
                            "score_watering": int(genus_instance.meta.get("watering")),
                            "score_soil": genus_instance.meta.get("soil"),
                            "score_humidity": int(genus_instance.meta.get("humidity")),
                            "toxicity": genus_instance.meta.get("toxicity"),
                            "score_fertilizing": int(genus_instance.meta.get("fertilizing")),
                            "score_propagation": genus_instance.meta.get("propagation"),

                            "temperature": get_field(title, genus_instance.term.title, data, "temperature"),
                            "light": get_field(title, genus_instance.term.title, data, "light"),
                            "watering": get_field(title, genus_instance.term.title, data, "watering"),
                            "soil": get_field(title, genus_instance.term.title, data, "soil"),
                            "humidity": get_field(title, genus_instance.term.title, data, "humidity"),
                            "fertilizing": get_field(title, genus_instance.term.title, data, "fertilizer"),

                            "propagation": get_field(title, genus_instance.term.title, data, "propagation"),
                            "re-potting": get_field(title, genus_instance.term.title, data, "re-potting"),
                        },
                        options={}
                    )
                    for related in genus_instance.related.all():
                        test.terms.add(related)
                    test.terms.add(genus_instance)
                elif test.description is None:
                    test.description = description
                    test.save()
                print(test.title)
