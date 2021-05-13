from django.core.management.base import BaseCommand
from apps.cms.models import Post, Publication, PublicationTerm, Term
from apps.media.models import Media
import json
import random
import requests
from django.template.defaultfilters import slugify
import os
import re
import textwrap
from markdownify import markdownify as md


def convert_checklist(data):
    return {
        "title": data.get("title"),
        "child": list(map(lambda x: {
            "title": x.get("title"),
            "detail": md(x.get("content")),
        }, data.get("tasks")))
    }


class Command(BaseCommand):
    def handle(self, *args, **options):
        pub = Publication.objects.get(pk=28)
        name_folders = os.listdir("wiki_date")
        name_folders.sort()
        break_point = "March 31.json"
        start = False
        for file in name_folders:
            print(file)
            if file == break_point:
                start = True
            if not start:
                continue
            with open("wiki_date/{}".format(file)) as json_file:
                data = json.load(json_file)
                i = 0
                for elm in data:
                    i = i + 1
                    taxonomies = [
                        {"title": elm.get("heading"), "taxonomy": "category"},
                        {"title": elm.get("year"), "taxonomy": "year"},
                        {"title": elm.get("date"), "taxonomy": "date"}
                    ]

                    for ett in elm.get("entities"):
                        taxonomies.append({
                            "title": ett.get("title"),
                            "description": ett.get("description"),
                            "taxonomy": "entity"
                        })
                    cal_title = elm.get("txt")
                    if elm.get("heading") == 'Deaths' or elm.get("heading") == 'Births':
                        cal_title = "{} {} in {}, {}".format(
                            elm.get("txt"),
                            elm.get("heading").lower(),
                            elm.get("date"),
                            elm.get("year")
                        )
                    title = textwrap.shorten(
                        cal_title,
                        width=199,
                        placeholder=""
                    )
                    post, is_created = Post.objects.get_or_create(
                        title=title,
                        primary_publication=pub,
                        defaults={
                            "post_type": "post",
                            "status": "POSTED",
                            "show_cms": True,
                            "description": elm.get("txt") if len(elm.get("txt")) < 500 else None,
                            "content": elm.get("txt") if len(elm.get("txt")) >= 500 else None
                        }
                    )
                    if is_created:
                        for tax in taxonomies:
                            tax_term, is_created = Term.objects.get_or_create(slug=slugify(tax.get("title")), defaults={
                                "title": tax.get("title")
                            })
                            ori_term_pub, is_created = PublicationTerm.objects.get_or_create(
                                publication=pub,
                                term=tax_term,
                                taxonomy=tax.get("taxonomy")
                            )
                            post.terms.add(ori_term_pub)
