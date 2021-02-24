from django.core.management.base import BaseCommand
from apps.cms.models import Post, Publication, PublicationTerm
from django.template.defaultfilters import slugify
import json
import random


def get_field(title, genera, data, f):
    if data.get(f) is not None and len(data.get(f)) > 1:
        return random.choice(data.get(f)).replace("{{title}}", title).replace("{{genera}}", genera)
    return None


class Command(BaseCommand):
    def handle(self, *args, **options):
        genera_name = "calathea"
        raws = [
            {
                "title": "Colocasia Esculenta",
                "description": "Colocasia esculenta is a tropical plant grown primarily for its edible corms, a root vegetable most commonly known as taro, kalo, or godere. It is the most widely cultivated species of several plants in the family Araceae that are used as vegetables for their corms, leaves, and petioles."
            },
            {
                "title": "Colocasia Gigantea",
                "description": "Colocasia gigantea, also called giant elephant ear or Indian taro, is a 1.5–3 m tall herb with a large, fibrous, inedible corm, producing at its apex a whorl of large leaves. The leaf stalk is used as a vegetable in some areas in South East Asia and Japan."
            },
            {
                "title": "Colocasia Illustris",
                "description": "Colocasia esculenta 'Illustris' (Taro) is a tuberous, frost-tender perennial with huge, long-stalked, heart-shaped, blackish purple leaves adorned with dramatic bright green veins. The giant leaves can measure up to 3 ft.",
            }
        ]
        pub = Publication.objects.get(host="9plant.com")
        genus = PublicationTerm.objects.get(publication=pub, term__slug=genera_name, taxonomy="genus")

        with open('genera_export.json') as json_file:
            data = json.load(json_file)
            for raw in raws:
                test = Post.objects.filter(slug__startswith=slugify(raw.get("title")), post_type="plant",
                                           primary_publication=pub).first()
                if test is None:
                    test = Post.objects.create(
                        title=raw.get("title"),
                        post_type="plant",
                        description=raw.get("description"),
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

                            "temperature": get_field(raw.get("title"), genus.term.title, data, "temperature"),
                            "light": get_field(raw.get("title"), genus.term.title, data, "light"),
                            "watering": get_field(raw.get("title"), genus.term.title, data, "watering"),
                            "soil": get_field(raw.get("title"), genus.term.title, data, "soil"),
                            "humidity": get_field(raw.get("title"), genus.term.title, data, "humidity"),
                            "fertilizing": get_field(raw.get("title"), genus.term.title, data, "fertilizer"),

                            "propagation": get_field(raw.get("title"), genus.term.title, data, "propagation"),
                            "re-potting": get_field(raw.get("title"), genus.term.title, data, "re-potting"),
                        },
                        options={}
                    )
                    for related in genus.related.all():
                        test.terms.add(related)
                    test.terms.add(genus)
                else:
                    test.description = raw.get("description")
                    test.meta = {
                                    "score_temperature": int(genus.meta.get("temperature")),
                                    "score_light": int(genus.meta.get("light")),
                                    "score_watering": int(genus.meta.get("watering")),
                                    "score_soil": genus.meta.get("soil"),
                                    "score_humidity": int(genus.meta.get("humidity")),
                                    "toxicity": genus.meta.get("toxicity"),
                                    "score_fertilizing": int(genus.meta.get("fertilizing")),
                                    "score_propagation": genus.meta.get("propagation"),

                                    "temperature": get_field(raw.get("title"), genus.term.title, data, "temperature"),
                                    "light": get_field(raw.get("title"), genus.term.title, data, "light"),
                                    "watering": get_field(raw.get("title"), genus.term.title, data, "watering"),
                                    "soil": get_field(raw.get("title"), genus.term.title, data, "soil"),
                                    "humidity": get_field(raw.get("title"), genus.term.title, data, "humidity"),
                                    "fertilizing": get_field(raw.get("title"), genus.term.title, data, "fertilizer"),

                                    "propagation": get_field(raw.get("title"), genus.term.title, data, "propagation"),
                                    "re-potting": get_field(raw.get("title"), genus.term.title, data, "re-potting"),
                                }
                    test.save()
                test.status = "POSTED"
                test.save()
                print(test.title)
