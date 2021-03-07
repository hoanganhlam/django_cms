from django.core.management.base import BaseCommand
from apps.cms.models import Post, Publication, PublicationTerm, Term
from django.template.defaultfilters import slugify
import json
import random


class Command(BaseCommand):
    def handle(self, *args, **options):
        maker = Publication.objects.get(pk=3)
        sp = Publication.objects.get(pk=24)
        for post in sp.posts.all():
            print(post.id)
            post.post_type = "post"
            post.save()
        return
        for maker_post in maker.posts.all():
            if maker_post.meta is not None:
                if maker_post.meta.get("sheets"):
                    term, is_created = Term.objects.get_or_create(slug=maker_post.slug, defaults={
                        "title": maker_post.title
                    })
                    pub_term, is_created = PublicationTerm.objects.get_or_create(
                        term=term,
                        publication=sp,
                        defaults={
                            "description": maker_post.description,
                            "options": maker_post.options,
                        },
                        taxonomy=maker_post.post_type
                    )
                    for sheet in maker_post.meta.get("sheets"):
                        title = sheet.get("title")
                        if title is not None and len(title) < 200:
                            slug = "{}_{}".format(maker_post.slug, slugify(title))
                            meta = {
                                "rows": sheet.get("rows")
                            }
                            sp_post, is_created = Post.objects.get_or_create(
                                slug=slug,
                                defaults={
                                    "title": title,
                                    "show_cms": True,
                                    "meta": meta,
                                    "description": sheet.get("description") if sheet.get("description") and len(sheet.get("description")) < 500 else None,
                                    "content": sheet.get("description") if sheet.get("description") and len(sheet.get("description")) > 500 else None,
                                    "options": {
                                        "tasks": [],
                                        "done_tasks": [],
                                        "primary_term": pub_term.id
                                    },
                                    "primary_publication": sp,
                                    "status": "POSTED"
                                },
                            )
                            if not is_created:
                                if pub_term not in sp_post.terms.all():
                                    sp_post.terms.add(pub_term)
                            print(title)