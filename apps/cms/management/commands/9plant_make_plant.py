from django.core.management.base import BaseCommand
from apps.cms.models import Post, Publication, PublicationTerm
import json
import random


def get_field(title, genera, data, f):
    if data.get(f) is not None and len(data.get(f)) > 1:
        return random.choice(data.get(f)).replace("{{title}}", title).replace("{{genera}}", genera)
    return None


class Command(BaseCommand):
    def handle(self, *args, **options):
        genera_name = "calathea"
        pub = Publication.objects.get(host="9plant.com")
        genus = PublicationTerm.objects.get(publication=pub, term__slug=genera_name, taxonomy="genus")
        species = PublicationTerm.objects.filter(publication=pub, related=genus, term__title__startswith=genera_name.capitalize())
        with open('genera_export.json') as json_file:
            data = json.load(json_file)
            for sp in species:
                test = Post.objects.filter(slug__startswith=sp.term.slug, post_type="plant", primary_publication=pub).first()
                if test is None:
                    test = Post.objects.create(
                        title=sp.term.title,
                        post_type="plant",
                        description=sp.description,
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
                elif test.description is None:
                    test.description = sp.description
                    test.save()
                test.status = "POSTED"
                test.save()
                print(test.title)
