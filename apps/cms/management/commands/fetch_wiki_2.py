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
        genera = "Tillandsia"
        family = "Bromeliaceae"
        url = "https://en.wikipedia.org/wiki/List_of_Tillandsia_species"
        selector = "#mw-content-text > div.mw-parser-output  ul"
        with open('genera_export.json') as json_file:
            data = json.load(json_file)
        pub = Publication.objects.get(pk=7)
        genus_instance = PublicationTerm.objects.filter(term__slug=slugify(genera), taxonomy="genus").first()
        if genus_instance:
            r = requests.get(url)
            soup = BeautifulSoup(r.content, features="html.parser")
            elms = soup.select(selector)
            for elm in elms:
                lis = elm.select("li")
                for li in lis:
                    title = li.find(text=True).title()
                    description = None
                    media_url = None
                    if genera in title:
                        if title == genera or title == "Subsp. " or title == "Var. " or " X " in title or " Var. " in title or "†" in title:
                            continue
                        print(title)
                        test = Post.objects.filter(
                            slug__startswith=slugify(title),
                            post_type="plant",
                            primary_publication=pub).first()
                        if test is None:
                            if li.find("a") and "/wiki/" in li.find("a").get("href"):
                                r2 = requests.get(
                                    "https://en.wikipedia.org/api/rest_v1/page/summary/" + li.find("a").get(
                                        "href").replace(
                                        "/wiki/", ""))
                                r2_data = r2.json()
                                description = r2_data.get("extract")[:400]
                                if r2_data.get("originalimage"):
                                    media_url = r2_data.get("originalimage").get("source")
                            origins = []
                            authors = []

                            try:
                                if len(li.contents) > 3:
                                    for content in li.contents[3:]:
                                        if type(content) is Tag and content.name not in ["sup", "ul"]:
                                            origins = origins + content.find_all(text=True)
                                        elif type(content) is NavigableString and content not in [" - ", ", ", " (",
                                                                                                  ")"]:
                                            # if re.search(r'\((.*?)\)', content):
                                            #     origins = origins + re.search(r'\((.*?)\)', content).group(1).split(",")
                                            xxx = content.split("-")[1] if len(content.split("-")) > 1 else \
                                            content.split("-")[0]
                                            origins = origins + xxx.replace(" - ", "").split(",")
                                if li.find("small") is not None:
                                    authors.append(str(li.find("small").find(text=True)).strip())
                                elif len(li.contents) == 2 and li.contents[1]:
                                    authors.append(li.contents[1].strip())
                                # if len(li.contents) == 2:
                                #     content2 = li.contents[1].split(" - ")
                                #     # origins = list(map(lambda x: x.strip(), content2[1].split(",")))
                                #     authors = list(map(lambda x: x.strip(), content2[0].split(",")))
                            except Exception as e:
                                print(e)
                            origins = list(filter(lambda x: x not in ["(", " ", ")"], origins))
                            origins = list(map(lambda x: clean_origin(x), origins))

                            if description is None:
                                description_patterns = [
                                    "{title} is a species of plant in the family {family}"
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
                                description = description.replace("..", ".")
                            print(origins)
                            print(authors)
                            print(description)
                            meta = {
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
                            }
                            if media_url:
                                try:
                                    media = Media.objects.save_url(media_url)
                                    meta["media"] = media.id
                                except Exception as e:
                                    print(e)

                            test = Post.objects.create(
                                title=title,
                                description=description,
                                post_type="plant",
                                primary_publication=pub,
                                status="POSTED",
                                meta=meta,
                                options={},
                                show_cms=media_url is not None
                            )
                            for related in genus_instance.related.all():
                                test.terms.add(related)
                            test.terms.add(genus_instance)
                            for ori in origins:
                                ori_term, is_created = Term.objects.get_or_create(slug=slugify(ori), defaults={
                                    "title": ori
                                })
                                ori_term_pub, is_created = PublicationTerm.objects.get_or_create(
                                    publication=pub,
                                    term=ori_term,
                                    taxonomy="origin"
                                )
                                test.terms.add(ori_term_pub)
                        else:
                            if test.description is None:
                                test.description = description
                                test.save()
                            for related in genus_instance.related.all():
                                if related not in test.terms.all():
                                    test.terms.add(related)
