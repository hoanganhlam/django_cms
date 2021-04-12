from django.core.management.base import BaseCommand
from apps.cms.models import Post, Publication, PublicationTerm, Term
from apps.media.models import Media
import json
import random
import requests
from django.template.defaultfilters import slugify
from os import listdir
from os.path import isfile, join
from os import walk


class Command(BaseCommand):
    def handle(self, *args, **options):
        pub = Publication.objects.get(pk=24)
        i = 0
        for filename in listdir("./out"):
            with open('./out/{}'.format(filename)) as json_file:
                print(filename)
                data = json.load(json_file)
                term, is_created = Term.objects.get_or_create(
                    slug=slugify(data.get("head").get("title")),
                    defaults={
                        "title": data.get("head").get("title")
                    }
                )
                pub_term, is_created = PublicationTerm.objects.get_or_create(
                    term=term,
                    taxonomy="cheat-sheet",
                    publication=pub,
                    defaults={
                        "show_cms": True,
                        "description": data.get("head").get("intro", data.get("head").get("description"))
                    }
                )
                if data.get("head").get("category"):
                    term, is_created = Term.objects.get_or_create(
                        slug=data.get("head").get("category"),
                        defaults={
                            "title": data.get("head").get("category")
                        }
                    )
                    category, is_created = PublicationTerm.objects.get_or_create(
                        term=term,
                        taxonomy="category",
                        publication=pub,
                        defaults={
                            "show_cms": True
                        }
                    )
                    pub_term.related.add(category)
                for section in data.get("body"):
                    title = section.get("title")
                    if title is None:
                        title = section.get("h2")
                        if title is None:
                            title = "Untitled"
                        slug = slugify(title)
                    elif section.get("h2"):
                        slug = "{}_{}".format(slugify(section.get("h2")), slugify(title))
                        title = "[{}] {}".format(section.get("h2"), title)
                    else:
                        slug = slugify(title)
                    post, is_created = Post.objects.get_or_create(
                        slug="{}_{}".format(pub_term.term.slug, slug),
                        primary_publication=pub,
                        defaults={
                            "content": section.get("elms"),
                            "title": title,
                            "show_cms": True,
                            "status": "POSTED",
                            "post_type": "post"
                        }
                    )
                    post.terms.add(pub_term)

