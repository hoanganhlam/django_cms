from django.core.management.base import BaseCommand
from apps.cms.models import Post, Publication, PublicationTerm
from apps.media.models import Media
import json
import random
import requests
from django.template.defaultfilters import slugify


def get_field(title, genera, data, f):
    if data.get(f) is not None and len(data.get(f)) > 1:
        return random.choice(data.get(f)).replace("{{title}}", title).replace("{{genera}}", genera)
    return None


class Command(BaseCommand):
    def handle(self, *args, **options):
        genera_name = "Yucca"
        family = "Asparagaceae"
        pub = Publication.objects.get(host="9plant.com")
        genus = PublicationTerm.objects.get(publication=pub, term__slug=genera_name.lower(), taxonomy="genus")
        species = PublicationTerm.objects.filter(
            publication=pub, related=genus,
            term__title__startswith=genera_name.capitalize()
        )
        addons = [
            "Yucca capensis", "Yucca carnerosana", "Yucca cernua", "Yucca coahuilensis", "Yucca constricta",
            "Yucca decipiens", "Yucca declinata", "Yucca desmetiana", "Yucca elata", "Yucca endlichiana",
            "Yucca filifera", "Yucca gigantea", "Yucca grandiflora", "Yucca intermedia", "Yucca jaliscensis",
            "Yucca lacandonica", "Yucca linearifolia", "Yucca mixtecana", "Yucca neomexicana", "Yucca periculosa",
            "Yucca potosina", "Yucca queretaroensis", "Yucca rostrata", "Yucca sterilis", "Yucca utahensis",
            "Yucca valida"
        ]
        with open('genera_export.json') as json_file:
            data = json.load(json_file)
            for sp in list(species) + addons:
                description = None
                media_url = None
                if type(sp) is str:
                    wiki_title = sp.replace(" ", "_")
                else:
                    wiki_title = sp.term.title.lower().replace(" ", "_").capitalize()
                try:
                    r2 = requests.get("https://en.wikipedia.org/api/rest_v1/page/summary/" + wiki_title)
                    r2_data = r2.json()
                    description = r2_data.get("extract")[:400]
                    if r2_data.get("originalimage"):
                        media_url = r2_data.get("originalimage").get("source")
                except Exception as e:
                    print(e)
                title = sp if type(sp) is str else sp.term.title
                if description is None and type(sp) is not str:
                    description = sp.term.description
                if description is None:
                    description_patterns = [
                        "{title} is a species of plant in the family {family}"
                        "{title} is a species of flowering plant in the {genera_name} family {family}",
                        "{title} is a species of {genera_name}",
                        "{title} is a perennial species in the genus {genera_name}, belonging to the family {family}",
                        "{title} is a plant in the family {family}",
                    ]
                    description = random.choice(description_patterns).format(
                        title=title,
                        genera_name=genera_name,
                        family=family
                    )
                print(wiki_title)
                print(title)
                print(description)
                test = Post.objects.filter(
                    slug=slugify(title),
                    post_type="plant",
                    primary_publication=pub).first()
                if test is None:
                    meta = {
                        "score_temperature": int(genus.meta.get("temperature")),
                        "score_light": int(genus.meta.get("light")),
                        "score_watering": int(genus.meta.get("watering")),
                        "score_soil": genus.meta.get("soil"),
                        "score_humidity": int(genus.meta.get("humidity")),
                        "toxicity": genus.meta.get("toxicity"),
                        "score_fertilizing": int(genus.meta.get("fertilizing")),
                        "score_propagation": genus.meta.get("propagation"),
                        "temperature": get_field(title, genera_name, data, "temperature"),
                        "light": get_field(title, genera_name, data, "light"),
                        "watering": get_field(title, genera_name, data, "watering"),
                        "soil": get_field(title, genera_name, data, "soil"),
                        "humidity": get_field(title, genera_name, data, "humidity"),
                        "fertilizing": get_field(title, genera_name, data, "fertilizer"),
                        "propagation": get_field(title, genera_name, data, "propagation"),
                        "re-potting": get_field(title, genera_name, data, "re-potting"),
                    }
                    if media_url:
                        try:
                            media = Media.objects.save_url(media_url)
                            meta["media"] = media.id
                        except Exception as e:
                            print(e)
                    test = Post.objects.create(
                        title=title.title(),
                        post_type="plant",
                        description=description,
                        primary_publication=pub,
                        status="POSTED",
                        meta=meta,
                        options={},
                        show_cms=media_url is not None
                    )
                    for related in genus.related.all():
                        test.terms.add(related)
                    test.terms.add(genus)
                    # if type(sp) is str:
                    #     for related in genus.related.all():
                    #         test.terms.add(related)
                    #     test.terms.add(genus)
                    # else:
                    #     for related in sp.related.all():
                    #         test.terms.add(related)
                print(test.title)
