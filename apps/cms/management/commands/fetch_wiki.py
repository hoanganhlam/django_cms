from django.core.management.base import BaseCommand
import requests
from bs4 import BeautifulSoup
from apps.cms.models import PublicationTerm, Publication, Term
import random

from bs4.element import Tag, NavigableString


class Command(BaseCommand):
    def handle(self, *args, **options):
        genera = "Calathea"
        url = "https://en.wikipedia.org/wiki/Calathea"
        terms = {
            "phylum": "Monocotyledon",
            "class": "Commelinids",
            "order": "Zingiberales",
            "family": "Marantaceae",
            "genera": genera,
        }
        publication = Publication.objects.get(pk=7)
        publication_terms = []
        for key in terms.keys():
            if terms.get(key):
                publication_terms.append(PublicationTerm.objects.get(
                    taxonomy=key,
                    term__title=terms.get(key),
                    publication=publication
                ))
        r = requests.get(url)
        soup = BeautifulSoup(r.content, features="html.parser")
        elms = soup.select("#mw-content-text > div.mw-parser-output > ul:nth-child(16)")
        for elm in elms:
            lis = elm.select("li")
            for li in lis:
                title = li.find(text=True)
                if title == "Calathea":
                    continue
                print(title)
                origins = []
                if len(li.contents) > 3:
                    for content in li.contents[3:]:
                        if type(content) is Tag and content.name not in ["sup", "ul"]:
                            origins = origins + content.find_all(text=True)
                        elif type(content) is NavigableString and content not in [" - ", ", ", " (", ")"]:
                            origins = origins + content.replace(" - ", "").split(",")
                description_patterns = [
                    "{title} is a species of {genera} found in {origin}.",
                    "{title} is a perennial species in the genus {genera}, belonging to the family Araceae. This species can be found in {origin}."
                ]
                description = description_patterns[random.randrange(0, 1)].format(
                    title=title, origin=", ".join(origins),
                    genera=genera) if len(origins) > 0 else None
                pub_term_origins = []
                # for origin in origins:
                #     x = Term.objects.filter(title__iexact=origin.title()).first()
                #     if x is None:
                #         x = Term.objects.create(title=origin.title())
                #     y, is_created = PublicationTerm.objects.get_or_create(
                #         publication=publication,
                #         term=x,
                #         taxonomy="origin"
                #     )
                #     pub_term_origins.append(y)
                term = Term.objects.filter(title__iexact=title.title()).first()
                if term is None:
                    term = Term.objects.create(title=title.title())
                species, created = PublicationTerm.objects.get_or_create(
                    publication=publication,
                    taxonomy="species",
                    term=term,
                    defaults={
                        "description": description
                    }
                )
                if created:
                    species_related = species.related.all()
                    for p_term in publication_terms:
                        if p_term not in species_related:
                            species.related.add(p_term)
                    for p_term in pub_term_origins:
                        if p_term not in species_related:
                            species.related.add(p_term)
