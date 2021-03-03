from django.core.management.base import BaseCommand
from apps.cms.models import Post, Publication, PublicationTerm, Term
from django.template.defaultfilters import slugify
import json
import random


class Command(BaseCommand):
    def handle(self, *args, **options):
        nine = Publication.objects.get(pk=7)
        universe = Publication.objects.get(pk=15)
        plants = Post.objects.filter(primary_publication=nine, post_type="plant")
        for plant in plants:
            str_tags = [slugify(plant.title).replace("-", "")]
            tags = plant.terms.filter(taxonomy="tag")
            for tag in tags:
                str_tags.append(slugify(tag.term.title).replace("-", ""))
            for str_tag in str_tags:
                term, t_created = Term.objects.get_or_create(
                    slug=str_tag,
                    defaults={
                        "title": str_tag
                    }
                )
                u_tag, u_created = PublicationTerm.objects.get_or_create(
                    term=term,
                    taxonomy="tag",
                    publication=universe
                )
                if u_tag not in tags:
                    plant.terms.add(u_tag)

                for post in u_tag.posts.filter(post_type="post"):
                    if plant not in post.post_related.all():
                        post.post_related.add(plant)
            print(plant.title)